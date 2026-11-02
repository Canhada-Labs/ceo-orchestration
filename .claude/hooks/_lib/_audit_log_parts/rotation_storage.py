"""Rotation, safe storage, and append declarations."""
from __future__ import annotations

def rotate_if_needed(log_path: Path, threshold_bytes: int) -> Optional[Path]:
    """Rename log_path to a monthly rotated file if it exceeds the threshold.

    Must be called UNDER the lock so no concurrent writer can race.

    PLAN-045 Wave 2 P0-08: delegates to ``_lib.audit_rotation.rotate_if_needed``
    so both write paths (this ``append_entry`` + ``_lib.audit_emit._write_event``)
    share identical rotation semantics. Preserves the existing call
    signature for backwards compatibility.

    PLAN-044 audit-v2 C6-P0-02 fix (Wave B): on successful rotation,
    invoke ``audit_hmac.reset_chain_on_rotation()`` so the HMAC chain
    starts a fresh genesis on the new log file. Without this, rotated
    logs continue chain from the previous final hmac into the new
    file's genesis row, which `audit-verify-chain.py` cannot validate
    (genesis is by definition prev_hmac=GENESIS_PREV; a non-genesis
    prev_hmac after rotation looks like silent tamper). Pattern was
    already correct in ``_lib.audit_emit._write_event`` — Wave B brings
    ``audit_log.py`` to parity.

    Returns the rotated path if rotation happened, None otherwise.
    """
    try:
        from _lib.audit_rotation import rotate_if_needed as _shared_rotate
    except ImportError:
        # Defensive: if the shared primitive isn't available (partial
        # install), fall back to the inlined legacy implementation so
        # rotation still works in the classic path.
        rotated = _legacy_rotate_inline(log_path, threshold_bytes)
    else:
        rotated = _shared_rotate(log_path, threshold_bytes, now_month_slug())

    # PLAN-044 audit-v2 C6-P0-02 — reset the per-process HMAC chain
    # state so the next entry written to the fresh log file is a
    # GENESIS_PREV-rooted row. Best-effort: missing _lib.audit_hmac
    # is non-fatal (older installs); chain integrity tests will catch
    # any rotated row that violates the genesis rule.
    if rotated is not None:
        try:
            from _lib import audit_hmac as _audit_hmac
            if hasattr(_audit_hmac, "reset_chain_on_rotation"):
                _audit_hmac.reset_chain_on_rotation()
        except Exception:
            pass
    return rotated


def _legacy_rotate_inline(
    log_path: Path, threshold_bytes: int
) -> Optional[Path]:
    """Fallback rotation for the rare case ``_lib.audit_rotation`` is missing.

    Kept in-line so a half-installed framework still rotates. Mirrors
    the behavior of the shared primitive byte-for-byte.
    """
    try:
        if not log_path.is_file():
            return None
        size = log_path.stat().st_size
        if size <= threshold_bytes:
            return None
    except OSError:
        return None

    month = now_month_slug()
    base = log_path.parent / f"{log_path.stem}-{month}.jsonl"
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = log_path.parent / f"{log_path.stem}-{month}-{counter}.jsonl"
        counter += 1
        if counter > 1000:
            return None

    try:
        os.replace(str(log_path), str(candidate))
    except OSError:
        return None
    return candidate


# -----------------------------------------------------------------------------
# Error breadcrumb
# -----------------------------------------------------------------------------


def write_breadcrumb(err_path: Path, message: str) -> None:
    """Best-effort write to the errors log. Never raises."""
    try:
        err_path.parent.mkdir(parents=True, exist_ok=True)
        ts = now_iso_utc()
        with open(err_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except OSError:
        # Last-resort: stderr
        try:
            sys.stderr.write(f"[audit-log] breadcrumb write failed: {message}\n")
        except Exception:  # pragma: no cover
            pass


# -----------------------------------------------------------------------------
# PLAN-045 F-01-06 — symlink + ownership defense
# -----------------------------------------------------------------------------


def _is_safe_audit_path(
    path: Path, expected_uid: int
) -> Tuple[bool, str]:
    """Check audit path for symlink + ownership safety.

    Returns ``(True, "")`` if safe (nonexistent OR real file/dir owned
    by ``expected_uid``). Returns ``(False, reason)`` if unsafe
    (symlink OR owner mismatch).

    Uses ``os.lstat`` (not ``stat``) so symlinks themselves are
    inspected rather than their targets. Never raises.

    ## Threat model

    1. **Symlink redirection.** An attacker with write access to
       ``$HOME/.claude/projects/`` creates
       ``ceo-orchestration -> /tmp/evil``. Every append goes to
       attacker-controlled path, defeats tamper-evident audit trail.
    2. **UID squatting.** Another user's process creates the audit
       directory. Hook runs as current user → fails to open for
       append (EACCES) OR leaks sensitive data into foreign-owned
       file if perms are too permissive.

    Both are refused before any write. The caller logs a breadcrumb
    to the /tmp fallback path and returns silently (fail-open on
    session; forensic trail preserved).
    """
    try:
        st = path.lstat()
    except FileNotFoundError:
        # Nonexistent is safe — the normal first-write path.
        return (True, "")
    except OSError as e:
        return (False, f"lstat_error:{e.__class__.__name__}")
    if stat.S_ISLNK(st.st_mode):
        return (False, "symlink_rejected")
    if st.st_uid != expected_uid:
        return (
            False,
            f"uid_mismatch:owner={st.st_uid} proc={expected_uid}",
        )
    return (True, "")


def _fallback_security_breadcrumb(message: str) -> None:
    """Breadcrumb to ``/tmp`` fallback when primary audit dir is unsafe.

    Mirrors ``_lib.audit_emit._fallback_log_path`` pattern. Never
    raises. Writes under the current user's namespaced filename so
    multi-user systems don't clobber each other.
    """
    try:
        try:
            user = getpass.getuser() or "unknown"
        except Exception:
            user = os.environ.get("USER") or "unknown"
        user = "".join(
            c for c in user if c.isalnum() or c in ("-", "_", ".")
        )
        fallback = Path("/tmp") / f"ceo-audit-fallback-{user}.log"
        ts = now_iso_utc()
        with open(fallback, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] audit-log security: {message}\n")
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Append entry under lock
# -----------------------------------------------------------------------------


def append_entry(
    entry: Dict[str, Any],
    *,
    paths: Dict[str, Path],
    threshold_bytes: int,
) -> None:
    """Append a single JSONL line under the lock, rotating if needed.

    Any failure is logged to the errors breadcrumb and swallowed (fail-open).

    PLAN-045 F-01-06: pre-write symlink + ownership check on audit dir
    and audit log file. On violation, breadcrumb to /tmp fallback +
    return silently (fail-open on session; entry dropped but forensic
    trail preserved via fallback + upstream audit_emit).
    """
    # F-01-06 symlink + uid defense BEFORE any mkdir/write.
    # Rationale: an attacker who plants a symlink in the audit dir can
    # redirect writes. Ownership mismatch indicates another user's
    # process created the path. Both warrant refusal + breadcrumb.
    expected_uid = os.geteuid()
    ok, reason = _is_safe_audit_path(paths["dir"], expected_uid)
    if not ok:
        _fallback_security_breadcrumb(
            f"audit dir unsafe: {paths['dir']} ({reason})"
        )
        return
    ok, reason = _is_safe_audit_path(paths["log"], expected_uid)
    if not ok:
        _fallback_security_breadcrumb(
            f"audit log unsafe: {paths['log']} ({reason})"
        )
        return
    # Ensure dir exists with restrictive perms
    # PLAN-024 F-sec-001 P1 fix: mkdir(mode=0o700) closes TOCTOU micro-window
    # between mkdir() and os.chmod() where same-UID attacker could win a race.
    try:
        paths["dir"].mkdir(parents=True, exist_ok=True, mode=0o700)
        # Belt-and-braces: retighten in case dir pre-existed with looser perms
        try:
            os.chmod(paths["dir"], 0o700)
        except OSError:
            pass
    except OSError as e:
        write_breadcrumb(paths["err"], f"cannot create audit dir: {e}")
        return

    # PLAN-085 Wave B.3 — inline HMAC computation closes the two-writer
    # chain gap (F-C1-001 / T0-line-168 transition_violation root cause).
    # 100% of agent_spawn events now carry hmac field per ADR-055.
    # Reuses _lib/audit_hmac primitives; fail-OPEN per CLAUDE.md §5.
    # PLAN-194 (rc.1 condition 67): key, predecessor, HMAC, append and sidecar
    # share ONE FileLock (as in audit_emit/drain); read before it, a writer in
    # between forked the chain. Only the stateless import stays outside.
    entry.setdefault("hmac", None)
    entry.setdefault("hmac_error", None)
    _audit_hmac = None
    try:
        from _lib import audit_hmac as _audit_hmac
    except Exception as _b3_ie:
        entry["hmac"] = None
        entry["hmac_error"] = type(_b3_ie).__name__

    line = ""

    try:
        with FileLock(paths["lock"], timeout=2.5):
            # Rotate inside the lock so writers can't race past a rename
            rotated_to = rotate_if_needed(paths["log"], threshold_bytes)
            # ADR-055-AMEND-2 marker as line 1 BEFORE our HMAC reads the predecessor;
            # no marker on disk => never sign over a last-hmac that may name it.
            marker_ok = rotated_to is None or _emit_rotation_marker_under_lock(
                paths["log"], rotated_to, paths["err"])
            _b3_hmac_digest_bytes = None
            if _audit_hmac is not None and not marker_ok:
                entry["hmac"] = None
                entry["hmac_error"] = "chain_reset_marker_missing"
            elif _audit_hmac is not None:
                try:
                    if not _audit_hmac.is_disabled():
                        _b3_key = _audit_hmac.get_or_create_key()
                        _b3_prev = _audit_hmac.read_prev_hmac()  # WITH the lock held
                        _b3_hmac_digest_bytes = _audit_hmac.compute_entry_hmac(
                            _b3_key, _b3_prev,
                            {k: v for k, v in entry.items()
                             if k not in ("hmac", "hmac_error")},
                        )
                        entry["hmac"] = _audit_hmac.hex_digest(_b3_hmac_digest_bytes)
                except Exception as _b3_he:
                    _b3_hmac_digest_bytes = None
                    entry["hmac"] = None
                    entry["hmac_error"] = type(_b3_he).__name__
            # Serialize AFTER the hmac field is final (still under the lock).
            line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
            try:
                # PLAN-024 F-sec-002 P1 fix: os.open with mode=0o600 sets perms
                # at create-time, closing the default-umask window between
                # open() and os.chmod().
                fd = os.open(
                    paths["log"],
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o600,
                )
                with os.fdopen(fd, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    # PLAN-025 F-obs-002: flush + fsync so the append survives
                    # process/OS crash. Audit is source-of-truth for governance;
                    # silent loss after write() but before OS flush = forensic gap.
                    # Cost: one syscall per spawn (~200us). Tolerable vs the
                    # governance invariant "every spawn is recorded".
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        # AttributeError on platforms without fsync; OSError on
                        # read-only fds or closed streams. Both acceptable — the
                        # write already succeeded; fsync is best-effort durability.
                        pass
                # Belt-and-braces: retighten in case file pre-existed looser
                try:
                    os.chmod(paths["log"], 0o600)
                except OSError:
                    pass
                # PLAN-085 Wave B.3 — update last-hmac sidecar within lock
                # so the next writer reads the correct prev_hmac. Best-effort.
                if _b3_hmac_digest_bytes is not None and _audit_hmac is not None:
                    try:
                        _audit_hmac.write_last_hmac(_b3_hmac_digest_bytes)
                    except Exception:
                        pass
            except OSError as e:
                write_breadcrumb(paths["err"], f"append failed: {e}  line={line[:200]}")
    except FileLockTimeout:
        # Fail-open: entry dropped (never chained), session never blocked;
        # the HMAC only exists under the lock, so the breadcrumb lacks it.
        line = line or json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        write_breadcrumb(
            paths["err"],
            f"lock timeout (stale?)  would-log={line[:200]}",
        )
    except Exception as e:  # pragma: no cover
        write_breadcrumb(paths["err"], f"unexpected error: {e}")


def _emit_rotation_marker_under_lock(
    log_path: Path, rotated_to: Path, err_path: Path
) -> bool:
    """ADR-055-AMEND-2 marker (emitter/drain helper) after OUR rotation, lock held. True =
    marker on disk or chain off; False = no marker on disk (when its append failed, last-hmac
    already names it), so the caller signs nothing over it."""
    try:
        from _lib import audit_hmac as _ah
        if _ah.is_disabled():
            return True
        from _lib import audit_emit as _ae
        if _ae._emit_chain_reset_marker_under_lock(
                log=log_path, previous_archive_path=str(rotated_to),
                rotation_trigger="size_threshold") is not None:
            return True
        why = "helper returned None"
    except Exception as e:
        why = f"{type(e).__name__}: {e}"
    write_breadcrumb(err_path, f"chain_reset_marker not written ({why}); "
                     "this agent_spawn line is left unchained")
    return False


# -----------------------------------------------------------------------------
# PLAN-155 Wave 4 — Codex host-wire audit-chain path (SENT-CX-B / ADR-161)
# -----------------------------------------------------------------------------
#
# Under OpenAI Codex (CEO_HOOK_ADAPTER=codex) the same audit_log.py hook is
# registered on the PostToolUse `*` matcher (templates/codex/hooks.json) and,
# via the headless `scripts/codex-exec-wrapper.sh`, is fed synthesized
# SessionStart/Stop bracket envelopes. The codex path reads the codex host
# wire through the codex adapter and appends metadata-only records to the SAME
# HMAC chain via `_lib.audit_emit` (the single-writer emitter that verify_chain
# validates). Two NEW registered actions keep the per-tool append and the
# turn-level backstop COUNTABLE separately (PLAN-155 Wave 4-A / Wave 4-B):
#
#   PostToolUse (any tool)  -> emit_codex_tool_recorded   (per-tool append, A)
#   Stop / SubagentStop     -> emit_codex_turn_ended      (turn backstop, B)
#   SessionStart            -> emit_session_start          (boot bracket; only
#                              reached via the wrapper — production codex
#                              routes SessionStart to SessionStart.py, so there
#                              is no double-count)
#
# The claude (default) path below is UNCHANGED and byte-identical when
# CEO_HOOK_ADAPTER is unset/`claude`. Completeness residual (named, ADR-161 +
# degradation page): partial shell interception means a per-tool row may be
# absent — absence is not evidence of absence of activity. verify_chain() and
# the HMAC chain shape are untouched; this path only appends.

# Closed tool-name enum mirror of _lib.audit_emit._CODEX_TOOL_RECORDED_TOOL_NAME_ENUM.
# The codex adapter has already aliased apply_patch -> Write/Edit and
# spawn_agent -> Task before we see the event; here we only fold mcp__* down to
# `mcp_other` (MF-SEC-1) and leave the emitter to coerce any residual miss to
# `other`.
