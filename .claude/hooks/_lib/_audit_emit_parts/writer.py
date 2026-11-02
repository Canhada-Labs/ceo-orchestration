"""Audit persistence helpers bound into the audit_emit facade."""

from __future__ import annotations

__all__ = (
    "_FALLBACK_NOTIFIED",
    "_fallback_log_path",
    "_emit_fallback_banner_once",
    "_write_fallback",
    "_safe_target_ref_hash_field",
    "_accel_clamp_count",
    "_auto_compact_clamp_pct",
    "_e3_clamp01",
    "_e3_safe_path_hashes",
    "_safe_token_sha_field",
    "_federation_safe_path_hash",
    "_audit_dir",
    "_log_path",
    "_log_family_dir",
    "_lock_path",
    "_errors_path",
    "_utc_now_iso",
    "_breadcrumb",
    "_DEFAULT_ROTATE_AT_BYTES",
    "_rotate_threshold",
    "_now_month_slug",
    "_rotate_if_needed_safe",
    "_VALID_ROTATION_TRIGGERS",
    "_normalize_rotation_trigger",
    "_emit_chain_reset_marker_under_lock",
    "_write_event",
    "_preview",
)

_FALLBACK_NOTIFIED = False


def _fallback_log_path() -> Path:
    """Return the /tmp fallback audit path, user-scoped.

    Env override: ``CEO_AUDIT_LOG_FALLBACK_PATH`` for tests.
    """
    override = os.environ.get("CEO_AUDIT_LOG_FALLBACK_PATH")
    if override:
        return Path(override)
    try:
        user = getpass.getuser() or "unknown"
    except Exception:  # pragma: no cover
        user = os.environ.get("USER") or "unknown"
    user = "".join(c for c in user if c.isalnum() or c in ("-", "_", "."))
    return Path("/tmp") / f"ceo-audit-fallback-{user}.log"


def _emit_fallback_banner_once(primary: Path, fallback: Path, err: str) -> None:
    """Emit `::warning::` stderr banner once per session (F-CHAOS-1)."""
    global _FALLBACK_NOTIFIED
    if _FALLBACK_NOTIFIED:
        return
    _FALLBACK_NOTIFIED = True
    try:
        sys.stderr.write(
            f"::warning::audit-log write failed ({err}); "
            f"falling back to {fallback}. "
            f"Investigate writability of {primary.parent}.\n"
        )
        sys.stderr.flush()
    except Exception:  # pragma: no cover
        pass


def _write_fallback(event_line: str) -> bool:
    """Append ``event_line`` to fallback path with 0o600. Never raises."""
    try:
        fallback = _fallback_log_path()
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with fallback.open("a", encoding="utf-8") as f:
            f.write(event_line)
            # PLAN-025 F-obs-002 — durability on fallback path too; if the
            # primary failed and we're writing fallback, crash-safety matters
            # MORE than on the happy path.
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, AttributeError):
                pass
        try:
            os.chmod(fallback, 0o600)
        except OSError:
            pass
        return True
    except Exception as e:
        try:
            sys.stderr.write(
                f"[audit_emit] fallback write ALSO failed: {type(e).__name__}: {e}\n"
            )
            sys.stderr.flush()
        except Exception:  # pragma: no cover
            pass
        return False


def _safe_target_ref_hash_field(v):
    """Return a non-empty 12-hex (or shorter) lowercase hash, else '' (fail-closed;
    never echoes a rejected value such as a raw branch name a caller tried to stuff)."""
    s = str(v or "")
    if s and len(s) <= 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return ""


def _accel_clamp_count(v):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return 0 if n < 0 else (99 if n > 99 else n)


def _auto_compact_clamp_pct(v):
    """Coerce to an int percent in [0, 100]; 0 on malformed (never echoes)."""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return 0 if n < 0 else (100 if n > 100 else n)


def _e3_clamp01(v):
    """Coerce to 0/1 (enforced flag). Anything truthy-but-weird -> 0 (safe)."""
    try:
        return 1 if int(v) == 1 else 0
    except (TypeError, ValueError):
        return 0


def _e3_safe_path_hashes(v):
    """Keep only comma-joined 12-hex tokens; drop anything else (a caller
    that tries to stuff a raw path gets it silently dropped, never echoed)."""
    s = str(v or "")
    toks = []
    for t in s.split(","):
        t = t.strip()
        if t and len(t) <= 12 and all(c in "0123456789abcdef" for c in t):
            toks.append(t)
    return ",".join(toks)[:512]


def _safe_token_sha_field(v):
    """Return a 64-hex lowercase token hash, else '' (fail-closed; never
    echoes a rejected value such as a raw token a caller tried to stuff)."""
    s = str(v or "")
    if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
        return s
    return ""


def _federation_safe_path_hash(raw: str) -> str:
    """Return a 12-hex hash of a filesystem-path field (Sec MF-3 / LLM06).

    Mirrors :func:`_persona_demand_safe_hash` strictness: an already-12-hex
    value passes through (idempotent re-hash safe); anything else (a raw
    host path) is SHA-256'd and truncated to 12 hex chars so no path body
    can leak into the HMAC-chained audit log.
    """
    import hashlib

    s = str(raw or "").strip().lower()
    if len(s) == 12 and all(c in "0123456789abcdef" for c in s):
        return s
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:12]


def _audit_dir() -> Path:
    """Return the audit log directory (env-overridable; matches audit_log.py).

    PLAN-182 W1 (ADR-001 S318 amendment): the default delegates to the
    single family resolver — per-project native slug — instead of the
    four-month literal. ``CEO_AUDIT_LOG_DIR`` keeps its whole-dir
    precedence for tests/multi-log setups.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    return _runtime_paths.runtime_state_dir()


def _log_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    return _audit_dir() / "audit-log.jsonl"


def _log_family_dir() -> Path:
    """Return the dir the lock/errors sidecars must share with the LOG.

    PLAN-182 W1 family-atomicity cure (ADR-001 S318 amendment item 3):
    when ``CEO_AUDIT_LOG_PATH`` moves the log, the lock and errors
    FOLLOW its parent instead of staying on the default dir — the W0
    matrix measured that split leaving two projects with distinct logs
    serializing on one lock. ``.resolve().parent`` matches
    ``audit_hmac._audit_dir_from_env`` byte-for-byte so key, lock and
    errors co-locate under the same derivation.
    """
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env).resolve().parent
    return _audit_dir()


def _lock_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_LOCK")
    if env:
        return Path(env)
    return _log_family_dir() / "audit-log.lock"


def _errors_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_ERR")
    if env:
        return Path(env)
    return _log_family_dir() / "audit-log.errors"


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 second-precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _breadcrumb(message: str) -> None:
    """Append a failure breadcrumb. Fail-open: never raise."""
    try:
        err = _errors_path()
        err.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with err.open("a", encoding="utf-8") as f:
            f.write(f"{_utc_now_iso()} audit_emit: {message}\n")
    except Exception:  # pragma: no cover
        pass


_DEFAULT_ROTATE_AT_BYTES = 10 * 1024 * 1024


def _rotate_threshold() -> int:
    """Return the active rotation threshold (bytes).

    Mirrors `audit_log.rotate_threshold()` so both write paths use
    identical semantics. Env override: ``CEO_AUDIT_LOG_ROTATE_BYTES``.
    """
    env = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
    if env:
        try:
            val = int(env)
            if val > 0:
                return val
        except ValueError:
            pass
    return _DEFAULT_ROTATE_AT_BYTES


def _now_month_slug() -> str:
    """Return the current UTC year-month slug (YYYY-MM) for rotated files.

    Mirrors `audit_log.now_month_slug()`; kept local to avoid a runtime
    coupling on that module (audit_emit.py is a leaf `_lib/` primitive
    per ADR-002, audit_log.py is a hook entrypoint).
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _rotate_if_needed_safe(log_path: Path) -> Optional[Path]:
    """Invoke the shared rotation primitive; fail-open on any error.

    MUST be called UNDER the audit-log FileLock. Returns the rotated-to
    path on success or None if no rotation was performed.
    """
    if not _ROTATION_AVAILABLE or _shared_rotate_if_needed is None:
        return None
    try:
        return _shared_rotate_if_needed(
            log_path, _rotate_threshold(), _now_month_slug()
        )
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"rotate_if_needed exception: {type(e).__name__}: {e}")
        return None


_VALID_ROTATION_TRIGGERS = frozenset(
    (
        "size_threshold",
        "manual",
        "owner_rotation",
        "quarantine_pre_fix",
    )
)


def _normalize_rotation_trigger(value: object) -> str:
    """Coerce + validate a rotation_trigger against the closed enum.

    Truncates to 32 chars then fails OPEN to the common-case
    ``size_threshold`` for any value outside ``_VALID_ROTATION_TRIGGERS``.
    Fail-open (never raises) matches the audit-emit contract — the marker
    must still be written on rotation.
    """
    s = str(value)[:32]
    if s not in _VALID_ROTATION_TRIGGERS:
        return "size_threshold"
    return s


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _emit_chain_reset_marker_under_lock(
    log: Path,
    previous_archive_path: str,
    rotation_trigger: str = "size_threshold",
) -> Optional[bytes]:
    """Emit chain_reset_marker as line 1 + write rotation manifest.

    Caller MUST hold the canonical FileLock + the canonical log file
    MUST be empty (just rotated). Returns the marker HMAC bytes on
    success or None on failure (caller breadcrumbs + falls back to
    legacy-mode rotation without marker).

    Side effects under the lock (sidecars-before-marker order per
    Codex R3 P1 fold — partial-failure recoverable):
    1. Read rotated archive's last hmac (best-effort; "" if not found)
    2. Compute marker HMAC at GENESIS_PREV (marker is genesis-anchored)
    3. **Write rotation manifest sidecar FIRST** (fail-closed: return None
       if fails — marker not on disk, next emit uses legacy mode)
    4. **Write audit-log.last-hmac with marker HMAC** (fail-closed: revert
       manifest, return None — both sidecars in pre-marker state)
    5. Write audit-log.chain-length to 1 (non-critical canary; fail-open
       with breadcrumb)
    6. **Append marker line LAST to new audit-log.jsonl** (line 1; if this
       fails, sidecars + manifest already consistent → verifier in
       manifest-required mode tamper-flags the missing line 1 marker,
       which is correct fail-LOUD detection)

    Pre-R3 order was: append-then-sidecars (marker on disk before manifest
    write); a sidecar failure could leave marker on disk + stale sidecars,
    causing the NEXT emit to chain from genesis and produce a broken
    line 2. The sidecars-first ordering eliminates this failure mode.
    """
    from datetime import datetime, timezone

    try:
        # Step 1: read rotated archive's last hmac.
        previous_archive_last_hmac = ""
        try:
            archive_path = Path(previous_archive_path)
            if archive_path.exists() and archive_path.stat().st_size > 0:
                # Read last non-empty line from archive
                with open(archive_path, "rb") as f:
                    f.seek(0, 2)  # seek to end
                    file_size = f.tell()
                    # Read last 4KB (sufficient for one JSONL line)
                    seek_to = max(0, file_size - 4096)
                    f.seek(seek_to)
                    tail = f.read().decode("utf-8", errors="replace")
                    last_line = ""
                    for line in tail.splitlines():
                        line = line.strip()
                        if line:
                            last_line = line
                    if last_line:
                        try:
                            last_entry = json.loads(last_line)
                            if isinstance(last_entry, dict):
                                hmac_val = last_entry.get("hmac")
                                if isinstance(hmac_val, str) and len(hmac_val) == 64:
                                    previous_archive_last_hmac = hmac_val
                        except json.JSONDecodeError:
                            pass
        except (OSError, AttributeError):
            pass

        # Step 2: compute marker HMAC at GENESIS_PREV (genesis-anchored).
        rotated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        marker_event = {
            "action": "chain_reset_marker",
            "previous_archive_path": str(previous_archive_path)[:256],
            "previous_archive_last_hmac": previous_archive_last_hmac[:64],
            "rotation_ts": rotated_at,
            "rotation_trigger": _normalize_rotation_trigger(rotation_trigger),
            "session_id": "",
            "project": "",
            "event_schema": "v2",
            "ts": rotated_at,
            "tokens_in": None,
            "tokens_out": None,
            "tokens_total": None,
        }
        key = _audit_hmac.get_or_create_key()
        marker_sans_hmac = {
            k: v for k, v in marker_event.items() if k != "hmac" and k != "hmac_error"
        }
        try:
            marker_digest = _audit_hmac.compute_entry_hmac(
                key, _audit_hmac.GENESIS_PREV, marker_sans_hmac
            )
        except _audit_hmac.AuditProducerPathPollutionError as ppe:
            # PLAN-118 AC-B4 chokepoint 1 + recursion-safety case 3 —
            # detected at the marker chokepoint itself. SKIP the marker
            # emission entirely (the marker would otherwise be signed
            # under the polluted producer's canonicalization, perpetuating
            # the exact bug we're closing). Write ONE bounded breadcrumb
            # line directly to the host's audit-log via the pre-canonical
            # fast-path (stdlib `open(path, 'a')` JSON write — NO
            # _write_event, NO compute_entry_hmac re-entry, NO chain
            # anchoring). The breadcrumb is non-chain-anchored advisory;
            # the chain head is what we're protecting.
            _breadcrumb(f"chain_reset_marker SKIPPED (producer path pollution): {ppe}")
            # Parse the exception message to extract closed-enum fields.
            # The exception message format is:
            #   "non_canonical_lib_resolution: reason_code=<rc> "
            #   "path_sha256_prefix=<8hex> "
            #   "expected_canonical_prefix=<8hex>"
            try:
                _msg = str(ppe)
                _rc = "audit_emit_path_pollution"  # safe default
                _psp = "00000000"
                _ecp = "00000000"
                for _tok in _msg.split():
                    if _tok.startswith("reason_code="):
                        _rc_candidate = _tok.split("=", 1)[1]
                        if _rc_candidate in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
                            _rc = _rc_candidate
                    elif _tok.startswith("path_sha256_prefix="):
                        _psp_candidate = _tok.split("=", 1)[1]
                        if len(_psp_candidate) == 8 and all(
                            c in "0123456789abcdef" for c in _psp_candidate
                        ):
                            _psp = _psp_candidate
                    elif _tok.startswith("expected_canonical_prefix="):
                        _ecp_candidate = _tok.split("=", 1)[1]
                        if len(_ecp_candidate) == 8 and all(
                            c in "0123456789abcdef" for c in _ecp_candidate
                        ):
                            _ecp = _ecp_candidate
                _breadcrumb_event = {
                    "action": "audit_producer_path_pollution_detected",
                    "ts": rotated_at,
                    "session_id": "",
                    "project": "",
                    "event_schema": "v2",
                    "tokens_in": None,
                    "tokens_out": None,
                    "tokens_total": None,
                    "hmac": None,
                    "hmac_error": "producer_path_pollution_detected",
                    "chokepoint": "chain_reset_marker",
                    "reason_code": _rc,
                    "path_sha256_prefix": _psp,
                    "expected_canonical_prefix": _ecp,
                }
                _line = json.dumps(_breadcrumb_event, ensure_ascii=False) + "\n"
                with log.open("a", encoding="utf-8") as _f:
                    _f.write(_line)
                    _f.flush()
            except Exception as _be:  # pragma: no cover
                _breadcrumb(
                    f"chain_reset_marker breadcrumb fast-path write failed: "
                    f"{type(_be).__name__}: {_be}"
                )
            return None
        marker_event["hmac"] = _audit_hmac.hex_digest(marker_digest)

        # PLAN-112-FOLLOWUP-hmac-tamper-fix Codex R3 P1 fold —
        # Sidecars-before-marker ordering: write all 3 sidecars FIRST,
        # then marker line LAST. If sidecar writes fail, marker is NOT
        # on disk yet → next emit handles via legacy chain-from-genesis
        # (recoverable). If sidecar succeeds + marker fails: revert
        # sidecars to pre-marker state (delete manifest + reset chain).
        # This makes partial-failure states recoverable + fail-closed
        # rather than silently mischaining line 2.

        # Step 3 (was 4): write rotation manifest sidecar FIRST
        try:
            _audit_hmac.write_rotation_manifest(
                previous_archive_filename=str(Path(previous_archive_path).name),
                rotated_at=rotated_at,
            )
        except _audit_hmac.AuditHmacError as me:
            _breadcrumb(
                "chain_reset_marker manifest write FAIL-CLOSED: {e}".format(e=me)
            )
            return None  # marker not on disk; next emit uses legacy mode

        # Step 4 (was 5): update last-hmac sidecar with marker's HMAC.
        try:
            _audit_hmac.write_last_hmac(marker_digest)
        except _audit_hmac.AuditHmacError as me:
            # Sidecar update failed; revert manifest write
            try:
                _audit_hmac.delete_rotation_manifest()
            except Exception:
                pass
            _breadcrumb(
                "chain_reset_marker last_hmac write FAIL-CLOSED: {e}".format(e=me)
            )
            return None

        # Step 5 (was 6): update chain-length to 1 (marker is HMAC-bearing).
        try:
            _audit_hmac.write_chain_length(1)
        except _audit_hmac.AuditHmacError as ce:
            # Chain-length is detection-canary; non-critical
            _breadcrumb(
                "chain_reset_marker chain_length write failed (non-blocking): "
                "{e}".format(e=ce)
            )

        # Step 6 (was 3): NOW append marker as line 1 of (current) new log.
        # If this fails, sidecars are already in marker-consistent state
        # but no line on disk — this is also recoverable: next sync emit
        # will see last-hmac=marker_digest and chain from it; the missing
        # marker line means verifier (manifest-mode) will tamper-flag
        # line 1, which is correct: marker IS required if manifest exists.
        line = json.dumps(marker_event, ensure_ascii=False) + "\n"
        try:
            with log.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError):
                    pass
        except OSError as we:
            # Marker line write failed. Sidecars already point at marker
            # HMAC + manifest exists → verifier will tamper-flag the
            # marker-missing state on next verify (correct fail-loud
            # behavior). Caller breadcrumbs.
            _breadcrumb("chain_reset_marker line write FAIL-LOUD: {e}".format(e=we))
            return None

        return marker_digest
    except Exception as e:  # pragma: no cover
        _breadcrumb(
            f"_emit_chain_reset_marker_under_lock failed: {type(e).__name__}: {e}"
        )
        return None


# QDSAA-FUNCAO-LONGA: mantém a compatibilidade de dispatch e o lookup dinâmico da fachada.
def _write_event(event: Dict[str, Any]) -> None:
    """Write a single JSONL event under the shared lock.

    Fail-open: any exception writes a breadcrumb and returns silently.
    F-CHAOS-1 (PLAN-019): when the primary audit dir is unwritable, fall
    back to /tmp/ceo-audit-fallback-<user>.log with once-per-session banner.
    """
    try:
        log = _log_path()

        # Enforce mandatory fields
        if "action" not in event or event["action"] not in _KNOWN_ACTIONS:
            _breadcrumb(f"unknown action: {event.get('action')!r}")
            return

        # Always set event_schema + ts
        event.setdefault("event_schema", EVENT_SCHEMA_V2)
        event.setdefault("ts", _utc_now_iso())

        # Reserve nullable cost fields (AI specialist P5)
        event.setdefault("tokens_in", None)
        event.setdefault("tokens_out", None)
        event.setdefault("tokens_total", None)

        # PLAN-023 Phase B (ADR-055) — HMAC chain fields.
        # Additive; null when chain is disabled or key-read fails.
        event.setdefault("hmac", None)
        event.setdefault("hmac_error", None)

        # PLAN-094 Wave A.3 — spool-writer hot path (ADR-055-AMEND-1).
        # Default path: append to per-PID spool + occasional amortized drain.
        # Falls back to sync canonical write on kill-switch or any spool error.
        if (
            _SPOOL_WRITER_AVAILABLE
            and _spool_writer is not None
            and not _spool_writer.is_sync_mode()
        ):
            try:
                _spool_writer.spool_append(event)
                # PLAN-094-FOLLOWUP Wave A.3-fail-open (option B) — check
                # durability indicator; fall through to sync canonical
                # write if spool path silently swallowed an OSError.
                if _spool_writer.last_append_succeeded():
                    if _spool_writer.should_drain():
                        _spool_writer.drain_now()
                    return  # spool path succeeded
                _breadcrumb(
                    "spool_append silent drop; falling back to sync canonical write"
                )
                # fall through to sync canonical write below
            except Exception as se:  # pragma: no cover
                _breadcrumb(f"spool path fallback to sync: {type(se).__name__}: {se}")
                # fall through to sync canonical write below

        # Phase 1: attempt primary write under lock.
        try:
            log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with FileLock(str(_lock_path()), timeout=2.5):
                # PLAN-045 Wave 2 P0-07/08 rotation wire — invoke the
                # shared rotation primitive BEFORE computing the HMAC.
                # If rotation happens, reset the chain sidecar so the next
                # write re-anchors at genesis in the new (empty) file.
                # Fail-open: any rotation exception is breadcrumbed and
                # the write proceeds against the over-threshold log.
                rotated_to = _rotate_if_needed_safe(log)
                if rotated_to is not None and _HMAC_AVAILABLE:
                    try:
                        _audit_hmac.reset_chain_on_rotation()
                    except Exception as re:  # pragma: no cover
                        _breadcrumb(
                            f"reset_chain_on_rotation failed: {type(re).__name__}: {re}"
                        )
                    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — write
                    # chain_reset_marker as line 1 of new file + rotation
                    # manifest sidecar, per ADR-055-AMEND-2. Fail-open:
                    # if marker emit fails, manifest is NOT written, so
                    # verifier falls back to legacy mode (no marker
                    # enforcement on this rotation event).
                    if not _audit_hmac.is_disabled():
                        try:
                            _emit_chain_reset_marker_under_lock(
                                log=log,
                                previous_archive_path=str(rotated_to),
                                rotation_trigger="size_threshold",
                            )
                        except Exception as me:  # pragma: no cover
                            _breadcrumb(
                                f"chain_reset_marker emit failed (rotation "
                                f"proceeds without marker): "
                                f"{type(me).__name__}: {me}"
                            )

                # PLAN-023 Phase B — compute HMAC INSIDE the lock so the
                # read-modify-write sequence is atomic against concurrent
                # subprocess writes. Chain-fork defect (security review
                # §3b) avoided because prev_hmac read + compute + write +
                # sidecar update all happen under the same FileLock.
                if _HMAC_AVAILABLE and not _audit_hmac.is_disabled():
                    try:
                        key = _audit_hmac.get_or_create_key()
                        prev = _audit_hmac.read_prev_hmac()
                        entry_sans = {
                            k: v
                            for k, v in event.items()
                            if k != "hmac" and k != "hmac_error"
                        }
                        digest = _audit_hmac.compute_entry_hmac(key, prev, entry_sans)
                        event["hmac"] = _audit_hmac.hex_digest(digest)
                    except _audit_hmac.AuditProducerPathPollutionError as ppe:
                        # PLAN-118 AC-B4 chokepoint 2 — _write_event HMAC
                        # path. Stale `_lib` on sys.path was detected by
                        # audit_hmac._ensure_canonical_lib_modules at
                        # compute_entry_hmac entry. Fail-OPEN at host
                        # hook (line written with hmac=null + closed-enum
                        # hmac_error); fail-CLOSED for the chain (no
                        # signed bytes leak under stale canonicalization).
                        # User session NEVER blocked.
                        event["hmac"] = None
                        event["hmac_error"] = "producer_path_pollution_detected"
                        _breadcrumb(
                            f"hmac_error: producer_path_pollution_detected: {ppe}"
                        )
                    except _audit_hmac.AuditHmacError as he:
                        # Fail-open: record the error kind + proceed
                        # with hmac=null. Operator finds breadcrumbs in
                        # audit-log.errors.
                        event["hmac"] = None
                        event["hmac_error"] = type(he).__name__
                        _breadcrumb(f"hmac_error: {he}")
                    except Exception as he:  # pragma: no cover
                        event["hmac"] = None
                        event["hmac_error"] = type(he).__name__
                        _breadcrumb(f"hmac_unexpected: {type(he).__name__}: {he}")

                # Serialize AFTER the hmac field was populated so the
                # on-disk line matches the canonical form used to compute
                # the HMAC. ensure_ascii=False keeps Unicode; the HMAC
                # was computed on the NFC-normalized canonical form so
                # a verifier re-computing from the line gets the same
                # digest (json.loads → canonical_json.encode is lossless).
                line = json.dumps(event, ensure_ascii=False) + "\n"

                with log.open("a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
                try:
                    os.chmod(log, 0o600)
                except OSError:
                    pass

                # Update the last-hmac sidecar under the same lock so
                # the next writer sees the correct prev_hmac. Best-effort
                # (no fsync on sidecar per perf-engineer §10).
                if (
                    _HMAC_AVAILABLE
                    and event.get("hmac")
                    and not _audit_hmac.is_disabled()
                ):
                    try:
                        _audit_hmac.write_last_hmac(_audit_hmac.from_hex(event["hmac"]))
                    except _audit_hmac.AuditHmacError:
                        pass  # next read falls back to genesis

                # PLAN-044 audit-v2 C6-P0-03 fix: wire chain-length canary
                # increment under same FileLock, after the JSON line is
                # already on disk + last_hmac persisted. Detection aid for
                # tail-truncation; gate-on-event["hmac"] keeps counter
                # semantically aligned with verify_chain.verified_count.
                # Fail-open with breadcrumb (canary is detection-aid, not
                # correctness-critical). Ordering invariant: rotation ->
                # hmac compute -> JSON write+fsync -> write_last_hmac ->
                # canary increment. Future refactors must preserve order.
                if (
                    _HMAC_AVAILABLE
                    and event.get("hmac")
                    and not _audit_hmac.is_disabled()
                ):
                    try:
                        n = _audit_hmac.read_chain_length()
                        _audit_hmac.write_chain_length(n + 1)
                    except _audit_hmac.AuditHmacError as ce:
                        _breadcrumb(
                            "chain_length_canary_io_error: {cls}: {err}".format(
                                cls=type(ce).__name__, err=ce
                            )
                        )  # fail-open: counter may stay stale; verifier-side re-walk catches drift
            return  # primary write succeeded
        except FileLockTimeout:
            # M9 — previously the entry was DROPPED on lock-timeout
            # (only a breadcrumb), so a contended log silently lost audit
            # events — the opposite of the tamper-evidence contract. Route the
            # event to the /tmp fallback log instead of dropping it. `line` is
            # NOT in scope here (it is built INSIDE the lock body, which never
            # ran because FileLock.__enter__ timed out), so serialize a
            # best-effort fallback line from `event` directly. It carries
            # hmac=null — acceptable: the fallback log is an explicitly
            # degraded, un-chained durability path (see banner), and a
            # null-hmac line in fallback is strictly better than a lost event.
            _breadcrumb(f"lock timeout for action={event.get('action')!r}")
            try:
                _fallback_line = json.dumps(event, ensure_ascii=False) + "\n"
            except Exception:  # pragma: no cover — event unserializable
                _fallback_line = None
            if _fallback_line is not None:
                _emit_fallback_banner_once(log, _fallback_log_path(), "lock timeout")
                _write_fallback(_fallback_line)
            return
        except (OSError, PermissionError) as primary_err:
            # F-CHAOS-1: primary path unwritable → fallback + banner.
            _emit_fallback_banner_once(log, _fallback_log_path(), str(primary_err))
            _write_fallback(line)
            return
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"write_event exception: {type(e).__name__}: {e}")


def _preview(text: Optional[str], max_len: int = 120) -> str:
    """Redact + collapse whitespace + truncate to max_len.

    PLAN-087 Wave C.8: outer whitespace collapse removed. The
    redact_secrets call internally collapses whitespace already
    (see _lib/redact.py); the outer collapse was an O(N) no-op on
    the hot path that doubled the string scan cost for long inputs.
    str() coercion kept for defense-in-depth on Optional callers.
    KERNEL FILE - landed under CEO_KERNEL_OVERRIDE per ADR-116.
    """
    if not text:
        return ""
    redacted = _redact.redact_secrets(str(text))
    if len(redacted) > max_len:
        return redacted[: max_len - 1] + "…"
    return redacted
