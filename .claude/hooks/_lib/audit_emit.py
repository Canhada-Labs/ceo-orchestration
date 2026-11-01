"""Typed event emitters for audit-log.jsonl event stream v2.

Promotes audit-log.jsonl from single-event-type (`agent_spawn`) to a
typed event stream with discriminator field `action` covering spawns,
debate rounds, plan transitions, veto triggers, benchmark runs, and
lesson writes. See PLAN-004 Phase 1 + ADR-005.

## Design contract

- **Additive only.** v1 `agent_spawn` entries remain valid; no fields
  removed. `event_schema: "v2"` field marks new entries. Consumers
  tolerate unknown fields per AUDIT-LOG-SCHEMA.md §2 forward-compat.
- **Fail-open.** Any emission error writes breadcrumb to `audit-log.errors`
  and returns silently. Framework MUST NOT block on observability.
- **Concurrent-write safe.** Uses `_lib.filelock.FileLock` (same lock
  file as `audit_log.py`).
- **Redaction.** Free-text fields (`desc_preview`, `reason_preview`)
  pass through `_lib.redact.redact_secrets` before write.
- **Stdlib-only.** No new dependencies.

## Public API (pure functions)

    emit_debate_event(plan_id, round, phase, agent, artifact_path, ...)
    emit_plan_transition(plan_id, from_status, to_status, file_path, ...)
    emit_veto_triggered(hook, reason_code, reason_preview, blocked_tool, ...)
    emit_benchmark_run(benchmark_id, skill, pass_rate, median_score, ...)
    emit_lesson_write(lesson_id, archetype, scope_tags, trigger, ...)

All emitters are side-effect-only (return None). Unit tests use
`TestEnvContext` from `_lib.testing` for isolation.

## Reserved fields (writer-deferred)

Every v2 event reserves nullable `tokens_in`, `tokens_out`, `tokens_total`
fields for future per-event cost accounting (AI specialist proposal P5,
deferred to Sprint 6). Schema reservation is free today; back-filling
schema later would force consumer breakage.
"""

from __future__ import annotations

import json
import os
import re  # PLAN-154 — bounded-token field coercion (learning-loop actions)
import sys
import threading  # PLAN-088 W1.4 / M-12 rate-cap state lock
import time
import zlib  # PLAN-088 W1.4 / M-12 rate-cap sliding window
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import redact as _redact  # noqa: E402
from _lib import runtime_paths as _runtime_paths  # noqa: E402  # PLAN-182 W1 single resolver (ADR-001 S318)
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402

import getpass  # noqa: E402

# PLAN-023 Phase B (ADR-055) — HMAC chain integration. Import guarded
# so the module loads even if audit_hmac is unavailable during partial
# rollout; fail-open invariant covers the runtime path.
try:
    from _lib import audit_hmac as _audit_hmac  # noqa: E402
    _HMAC_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_hmac = None  # type: ignore[assignment]
    _HMAC_AVAILABLE = False

# PLAN-094 Wave A.3 — spool-writer hot-path wire-in (ADR-055-AMEND-1).
# Kill-switch: CEO_AUDIT_SYNC_MODE=1 reverts to pre-Wave-A sync-fsync-per-call.
try:
    from _lib import spool_writer as _spool_writer  # noqa: E402
    _SPOOL_WRITER_AVAILABLE = True
except Exception:  # pragma: no cover
    _spool_writer = None  # type: ignore[assignment]
    _SPOOL_WRITER_AVAILABLE = False

# F-CHAOS-1 (PLAN-019) — session-scoped one-shot banner guard. Prevents
# per-write banner spam when the primary audit dir stays unwritable.
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
                f"[audit_emit] fallback write ALSO failed: "
                f"{type(e).__name__}: {e}\n"
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


# ---------------------------------------------------------------------------
# PLAN-045 Wave 2 P0-07/08 rotation wire — shared with audit_log.py
# ---------------------------------------------------------------------------

# 10 MiB default rotation threshold (matches audit_log.DEFAULT_ROTATE_AT_BYTES).
# Overridable via CEO_AUDIT_LOG_ROTATE_BYTES for tests.
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


# Import guard for the shared rotation primitive. Fail-open: if the
# module is missing during partial rollout, `_rotate_if_needed_safe`
# becomes a no-op and the existing write path continues unchanged.
try:
    from _lib.audit_rotation import rotate_if_needed as _shared_rotate_if_needed  # noqa: E402
    _ROTATION_AVAILABLE = True
except Exception:  # pragma: no cover
    _shared_rotate_if_needed = None  # type: ignore[assignment]
    _ROTATION_AVAILABLE = False


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


# PLAN-120-FOLLOWUP WS-D (E4-F4) — single source of truth for the
# rotation_trigger closed enum. Previously the public helper
# emit_chain_reset_marker validated membership but the internal
# _emit_chain_reset_marker_under_lock (the path actually exercised on
# automatic rotation) did not, so a future/buggy internal caller could land
# an off-enum free-text trigger in the on-disk chain_reset_marker. Both
# helpers now route through _normalize_rotation_trigger().
_VALID_ROTATION_TRIGGERS = frozenset((
    "size_threshold", "manual", "owner_rotation", "quarantine_pre_fix",
))


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


# PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — helper to emit
# chain_reset_marker as line 1 of new (post-rotation) audit-log + write
# rotation manifest. MUST be called UNDER the audit-log FileLock by the
# caller. Per ADR-055-AMEND-2.
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
        marker_sans_hmac = {k: v for k, v in marker_event.items()
                            if k != "hmac" and k != "hmac_error"}
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
            _breadcrumb(
                f"chain_reset_marker SKIPPED (producer path pollution): {ppe}"
            )
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
                        if len(_psp_candidate) == 8 and all(c in "0123456789abcdef" for c in _psp_candidate):
                            _psp = _psp_candidate
                    elif _tok.startswith("expected_canonical_prefix="):
                        _ecp_candidate = _tok.split("=", 1)[1]
                        if len(_ecp_candidate) == 8 and all(c in "0123456789abcdef" for c in _ecp_candidate):
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
            _breadcrumb(
                "chain_reset_marker line write FAIL-LOUD: {e}".format(e=we)
            )
            return None

        return marker_digest
    except Exception as e:  # pragma: no cover
        _breadcrumb(
            f"_emit_chain_reset_marker_under_lock failed: "
            f"{type(e).__name__}: {e}"
        )
        return None


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
                _breadcrumb(
                    f"spool path fallback to sync: {type(se).__name__}: {se}"
                )
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
                            f"reset_chain_on_rotation failed: "
                            f"{type(re).__name__}: {re}"
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
                        entry_sans = {k: v for k, v in event.items()
                                      if k != "hmac" and k != "hmac_error"}
                        digest = _audit_hmac.compute_entry_hmac(
                            key, prev, entry_sans
                        )
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
                        _breadcrumb(
                            f"hmac_error: {he}"
                        )
                    except Exception as he:  # pragma: no cover
                        event["hmac"] = None
                        event["hmac_error"] = type(he).__name__
                        _breadcrumb(
                            f"hmac_unexpected: {type(he).__name__}: {he}"
                        )

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
                        _audit_hmac.write_last_hmac(
                            _audit_hmac.from_hex(event["hmac"])
                        )
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
                            "chain_length_canary_io_error: "
                            "{cls}: {err}".format(
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
                _emit_fallback_banner_once(
                    log, _fallback_log_path(), "lock timeout"
                )
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


def emit_credential_rotation_due(
    provider: str,
    age_days: int,
    warn_threshold_days: int = 75,
    max_threshold_days: int = 90,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a credential_rotation_due event (ADR-040 §4).

    Fired on every live call once the active API key is older than
    ``warn_threshold_days`` (default 75). The event does not block the
    call — it surfaces in the dashboard so the operator rotates before
    the 90-day hard cap. Credential value is NEVER in any field.
    """
    event: Dict[str, Any] = {
        "action": "credential_rotation_due",
        "provider": provider,
        "age_days": int(age_days),
        "warn_threshold_days": int(warn_threshold_days),
        "max_threshold_days": int(max_threshold_days),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


# ---------------------------------------------------------------------
# PLAN-028 + PLAN-029 Wave A — lifecycle + output-scan emit helpers
# (kernel-apply closeout 2026-04-19, ADR-056 + ADR-057)
# ---------------------------------------------------------------------


def emit_generic(action: str, **kwargs: Any) -> None:
    """Generic event dispatcher for Wave A lifecycle + output-scan hooks.

    Validates ``action`` against _KNOWN_ACTIONS and writes the event
    via _write_event (same filelock + HMAC chain as named emitters).
    Caller provides arbitrary keyword arguments which become event
    fields. No redaction applied by this entry point — callers must
    pre-redact any free-text fields before passing.

    Never raises. Unknown action → breadcrumb + silent return.

    Added via kernel-apply batch for PLAN-027 Wave A exhaustive
    closeout (session 35 post-ship). See ADR-056 §Implementation +
    ADR-057 §Audit event registration.

    PLAN-065 Phase 2 / ADR-098 — Sec MF-3 enforcement defense-in-depth.
    The typed wrappers `emit_ceo_boot_emitted` / `emit_ceo_boot_check_skipped`
    are the canonical entrypoints with field allowlist scrubbing. If a
    future caller invokes `emit_generic("ceo_boot_emitted", prompt=...)`
    directly, route through the same scrub so the field allowlist
    boundary cannot be bypassed (Codex S82 P1 #1 closure).
    """
    if action not in _KNOWN_ACTIONS:
        _breadcrumb(f"emit_generic: unknown action {action!r}")
        return
    event: Dict[str, Any] = {"action": action}
    event.update(kwargs)
    # PLAN-065 Phase 2 / ADR-098 — Sec MF-3 boundary enforcement.
    # Route ceo_boot_* through the scrub even on emit_generic path so
    # the allowlist cannot be bypassed by future direct callers.
    if action == "ceo_boot_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "ceo_boot_check_skipped":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_CHECK_SKIPPED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_check_skipped dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "optimizer_route_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["optimizer_route_recommended"])
        if dropped:
            _breadcrumb("emit_generic optimizer_route_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "fanout_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["fanout_recommended"])
        if dropped:
            _breadcrumb("emit_generic fanout_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "model_choice_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["model_choice_recommended"])
        if dropped:
            _breadcrumb("emit_generic model_choice_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "eval_task_completed":  # PLAN-133 C3 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _EVAL_TASK_COMPLETED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic eval_task_completed dropped: %s" % sorted(dropped)[:10])
    elif action == "rag_context_recommended":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["rag_context_recommended"])
        if dropped:
            _breadcrumb("emit_generic rag_context_recommended dropped: %s" % sorted(dropped)[:10])
    elif action == "codex_review_disabled":  # PLAN-122 WS12 — Sec MF-3
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["codex_review_disabled"])
        if dropped:
            _breadcrumb("emit_generic codex_review_disabled dropped: %s" % sorted(dropped)[:10])
    elif action == "codex_review_invoked":  # PLAN-122 WS3 + PLAN-132 — Sec MF-3 + S172 coercion
        if "review_status" in event and event.get("review_status") not in _CODEX_REVIEW_STATUS_ENUM:
            event["review_status"] = "other"
        if "review_source" in event and event.get("review_source") not in _CODEX_REVIEW_SOURCE_ENUM:
            event["review_source"] = "other"
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _safe_target_ref_hash_field(event.get("target_ref_hash"))
        event, dropped = _scrub_ceo_boot_event(event, _OPTIMIZER_ALLOWLISTS["codex_review_invoked"])
        if dropped:
            _breadcrumb("emit_generic codex_review_invoked dropped: %s" % sorted(dropped)[:10])
    elif action == "verify_after_edit_finding":  # PLAN-128 §7 — Sec MF-3 + S172 coercion
        if event.get("checker") not in _VERIFY_CHECKER_ENUM:
            event["checker"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["finding_count"] = _accel_clamp_count(event.get("finding_count"))
        event, dropped = _scrub_ceo_boot_event(event, _VERIFY_AFTER_EDIT_FINDING_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic verify_after_edit_finding dropped: %s" % sorted(dropped)[:10])
    elif action == "adequacy_gate_flag":  # PLAN-128 §7 — Sec MF-3 + S172 coercion
        if event.get("flag_reason") not in _ADEQUACY_REASON_ENUM:
            event["flag_reason"] = "other"
        if event.get("lang") not in _ACCEL_LANG_ENUM:
            event["lang"] = "other"
        event["flag_count"] = _accel_clamp_count(event.get("flag_count"))
        event, dropped = _scrub_ceo_boot_event(event, _ADEQUACY_GATE_FLAG_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic adequacy_gate_flag dropped: %s" % sorted(dropped)[:10])
    elif action == "quota_exhausted":  # PLAN-133 B5 — Sec MF-3 + S172 coercion
        if event.get("error_class") not in _QUOTA_ERROR_CLASS_ENUM:
            event["error_class"] = "unknown"
        if event.get("source") not in _QUOTA_ERROR_SOURCE_ENUM:
            event["source"] = "unknown"
        # http_status: keep only a small non-negative int, else drop the key.
        _hs = event.get("http_status")
        if not isinstance(_hs, int) or isinstance(_hs, bool) or _hs < 0 or _hs > 599:
            event.pop("http_status", None)
        event["attempt"] = _accel_clamp_count(event.get("attempt"))  # reuse 0..99 clamp
        event, dropped = _scrub_ceo_boot_event(event, _QUOTA_EXHAUSTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic quota_exhausted dropped: %s" % sorted(dropped)[:10])
    elif action == "context_auto_compacted":  # PLAN-133 D1 — Sec MF-3 + S172 coercion
        if event.get("reason") not in _AUTO_COMPACT_REASON_ENUM:
            event["reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(event.get("turns_since_last"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_AUTO_COMPACTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_auto_compacted dropped: %s" % sorted(dropped)[:10])
    elif action == "context_auto_compact_suppressed":  # PLAN-133 D1 — Sec MF-3 + S172 coercion
        if event.get("suppress_reason") not in _AUTO_COMPACT_SUPPRESS_REASON_ENUM:
            event["suppress_reason"] = "other"
        event["usage_pct"] = _auto_compact_clamp_pct(event.get("usage_pct"))
        if "reclaim_pct" in event:
            event["reclaim_pct"] = _auto_compact_clamp_pct(event.get("reclaim_pct"))
        if "turns_since_last" in event:
            event["turns_since_last"] = _accel_clamp_count(event.get("turns_since_last"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_auto_compact_suppressed dropped: %s" % sorted(dropped)[:10])
    elif action == "context_middle_out_degraded":  # PLAN-133 D5 — Sec MF-3 + S172 coercion
        if event.get("reason") not in _MIDDLE_OUT_REASON_ENUM:
            event["reason"] = "other"
        event["rung"] = _accel_clamp_count(event.get("rung"))
        event["degraded_count"] = _accel_clamp_count(event.get("degraded_count"))
        if "total_count" in event:
            event["total_count"] = _accel_clamp_count(event.get("total_count"))
        if "protect_last" in event:
            event["protect_last"] = _accel_clamp_count(event.get("protect_last"))
        if "reclaim_bucket" in event:
            event["reclaim_bucket"] = _accel_clamp_count(event.get("reclaim_bucket"))
        if "fits_after" in event:
            event["fits_after"] = bool(event.get("fits_after"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_middle_out_degraded dropped: %s" % sorted(dropped)[:10])
    elif action == "context_middle_out_degrade_failed":  # PLAN-133 D5 — Sec MF-3 + S172 coercion
        if event.get("reason") not in _MIDDLE_OUT_REASON_ENUM:
            event["reason"] = "other"
        event["rung"] = _accel_clamp_count(event.get("rung"))
        if "degraded_count" in event:
            event["degraded_count"] = _accel_clamp_count(event.get("degraded_count"))
        if "total_count" in event:
            event["total_count"] = _accel_clamp_count(event.get("total_count"))
        if "protect_last" in event:
            event["protect_last"] = _accel_clamp_count(event.get("protect_last"))
        if "reclaim_bucket" in event:
            event["reclaim_bucket"] = _accel_clamp_count(event.get("reclaim_bucket"))
        event, dropped = _scrub_ceo_boot_event(event, _CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic context_middle_out_degrade_failed dropped: %s" % sorted(dropped)[:10])
    elif action == "supply_chain_advisory_emitted":  # PLAN-133 E2 — Sec MF-3 coercion
        if event.get("verdict") not in _SUPPLY_CHAIN_VERDICT_ENUM:
            event["verdict"] = "ALLOW"          # safe default; never invents a BLOCK
        if event.get("reason") not in _SUPPLY_CHAIN_REASON_ENUM:
            event["reason"] = "unknown"
        if event.get("ecosystem") not in _SUPPLY_CHAIN_ECOSYSTEM_ENUM:
            event["ecosystem"] = "other"
        # package: bound length + strip control chars (public identifier, but bound it).
        pkg = str(event.get("package", ""))
        event["package"] = "".join(c for c in pkg if c.isprintable())[:128]
        event["advisory_count"] = _accel_clamp_count(event.get("advisory_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                "emit_generic supply_chain_advisory_emitted dropped: %s"
                % sorted(dropped)[:10])
    elif action == "spawn_tool_scope_violation":  # PLAN-133 E3 — Sec MF-3 + coercion
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        # `detail` is tool-NAMES + counts; bound length, drop any path-shaped
        # token defensively (a "/" or "\" in detail is dropped to "" — no echo).
        _d = str(event.get("detail") or "")[:96]
        if "/" in _d or "\\" in _d:
            _d = ""
        event["detail"] = _d
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_tool_scope_violation dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "spawn_depth_or_overlap_blocked":  # PLAN-133 E3 — Sec MF-3 + coercion
        if event.get("rail") not in _SPAWN_RAIL_ENUM:
            event["rail"] = "other"
        event["enforced"] = _e3_clamp01(event.get("enforced"))
        event["count"] = _accel_clamp_count(event.get("count"))  # reuse §7 0..99 clamp
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_depth_or_overlap_blocked dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "spawn_file_assignment_recorded":  # PLAN-133 E3 — Sec MF-3 + coercion
        event["path_hashes"] = _e3_safe_path_hashes(event.get("path_hashes"))
        event["path_count"] = _accel_clamp_count(event.get("path_count"))
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic spawn_file_assignment_recorded dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "action_required_held":  # PLAN-133 E6 — Sec MF-3 + coercion
        if event.get("kind") not in _ACTION_REQUIRED_KIND_ENUM:
            event["kind"] = "other"
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        if "expires_at" in event:
            try:
                event["expires_at"] = int(event.get("expires_at"))
            except (TypeError, ValueError):
                event["expires_at"] = 0
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_HELD_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic action_required_held dropped: %s" % sorted(dropped)[:10])
    elif action == "action_required_resumed":  # PLAN-133 E6 — Sec MF-3
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_RESUMED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic action_required_resumed dropped: %s" % sorted(dropped)[:10])
    elif action == "action_required_rejected":  # PLAN-133 E6 — Sec MF-3 + coercion
        if event.get("reject_reason") not in _ACTION_REQUIRED_REJECT_ENUM:
            event["reject_reason"] = "other"
        if "token_sha256" in event:
            event["token_sha256"] = _safe_token_sha_field(event.get("token_sha256"))
        event, dropped = _scrub_ceo_boot_event(event, _ACTION_REQUIRED_REJECTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic action_required_rejected dropped: %s" % sorted(dropped)[:10])
    elif action == "ceo_boot_persona_coverage_score":  # PLAN-093 Wave C.5
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_persona_coverage_score dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-104 Wave A.4b — persona_demand_* Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("persona_demand_*",
    # raw_target_path=...)` would persist the forbidden field verbatim.
    # Codex iter-1 P0 #4 + iter-4 P0 fold (re-hash target_ref_hash
    # in opened/unmet branches so a caller can't stuff a raw path
    # into the allowed target_ref_hash field).
    elif action == "persona_demand_opened":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_OPENED_ALLOWLIST
        )
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_opened dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_matched":
        if "match_modality" in event and event.get("match_modality") not in _PERSONA_MATCH_MODALITY_ENUM:
            event["match_modality"] = "native_spawn"  # PLAN-132 — S172 safe default
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_MATCHED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_matched dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_unmet":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_UNMET_ALLOWLIST
        )
        if "target_ref_hash" in event:
            event["target_ref_hash"] = _persona_demand_safe_hash(
                event.get("target_ref_hash", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_unmet dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_demand_waived":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_DEMAND_WAIVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_demand_waived dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "persona_coverage_synthesized":  # PLAN-106 Wave C
        # Closed-enum validation BEFORE scrub. Invalid enum → drop the
        # whole event with breadcrumb (deny-by-default; prevents a
        # buggy caller from polluting the 4×4 matrix with free text).
        archetype = str(event.get("archetype", ""))
        task_type = str(event.get("task_type", ""))
        source = str(event.get("source", ""))
        if archetype not in _PERSONA_COVERAGE_ARCHETYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"archetype {archetype!r} not in closed enum"
            )
            return
        if task_type not in _PERSONA_COVERAGE_TASK_TYPES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"task_type {task_type!r} not in closed enum"
            )
            return
        if source not in _PERSONA_COVERAGE_SOURCES:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"source {source!r} not in closed enum"
            )
            return
        # cell_id MUST be sha256[:8] (8 lowercase hex chars). Defensive
        # rebuild if caller passed a longer/non-hex value — always update
        # the event field so non-hex stripped values do not leak through.
        cell_id = str(event.get("cell_id", ""))[:8]
        if cell_id and not all(c in "0123456789abcdef" for c in cell_id):
            cell_id = ""
        event["cell_id"] = cell_id
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic persona_coverage_synthesized dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-090-FOLLOWUP Wave A.6 — claim producer pair Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("claim_emitted",
    # claim_id="/raw/path")` would persist forbidden raw text.
    # Codex iter-1 P0-3 + P0-4 + P1-1 folds (defensive rehash +
    # enum re-validation at emit_generic dispatch).
    elif action == "claim_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CLAIM_EMITTED_ALLOWLIST
        )
        if "claim_id" in event:
            event["claim_id"] = _safe_claim_id_hash(event.get("claim_id", ""))
        if "payload_hash" in event:
            event["payload_hash"] = _safe_payload_hash(event.get("payload_hash", ""))
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic claim_emitted dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "confidence_gate_verdict":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_VERDICT_ALLOWLIST
        )
        if "claim_id" in event:
            event["claim_id"] = _safe_claim_id_hash(event.get("claim_id", ""))
        if "verdict" in event:
            v = str(event["verdict"])[:16].lower()
            event["verdict"] = v if v in _CONFIDENCE_GATE_VERDICTS else "fail"
        if "verifier_outcome" in event:
            event["verifier_outcome"] = _safe_verifier_outcome(
                event["verifier_outcome"], ""
            )
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_verdict dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-100 Wave B — per-class block-mode Sec MF-3 wire-up.
    # Without these branches a direct `emit_generic("confidence_gate_blocked",
    # blocking_classes="unsanitized")` would persist non-list types.
    elif action == "confidence_gate_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_BLOCKED_ALLOWLIST
        )
        # Defensive — re-validate blocking_classes shape (list of short strings)
        raw_blocking = event.get("blocking_classes")
        if isinstance(raw_blocking, (list, tuple)):
            event["blocking_classes"] = [
                str(c)[:64] for c in raw_blocking if isinstance(c, str)
            ]
        else:
            event["blocking_classes"] = []
        if "fail_count" in event:
            try:
                event["fail_count"] = int(event["fail_count"])
            except (TypeError, ValueError):
                event["fail_count"] = 0
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_blocked dropped: "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "confidence_gate_fp_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIDENCE_GATE_FP_DRIFT_DETECTED_ALLOWLIST
        )
        # Defensive — re-validate numeric fields
        for f in ("window_days", "fpr_bps", "threshold_bps", "sample_n"):
            if f in event:
                try:
                    event[f] = int(event[f])
                except (TypeError, ValueError):
                    event[f] = 0
        if "drift_class" in event:
            event["drift_class"] = str(event["drift_class"])[:64]
        if "auto_demote_at" in event:
            event["auto_demote_at"] = str(event["auto_demote_at"])[:32]
        if "agent_name" in event:
            event["agent_name"] = str(event["agent_name"])[:64]
        if "source" in event:
            event["source"] = str(event["source"])[:32]
        if dropped:
            _breadcrumb(
                f"emit_generic confidence_gate_fp_drift_detected dropped: "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-070 Round 5 / Layer B (Codex R5-02 closure, 2026-05-05+) —
    # wire `mcp_canonical_guard_{allowed,blocked}` through the same
    # field-allowlist scrub used by `ceo_boot_*`. The `_scrub_ceo_boot_
    # event` helper is allowlist-agnostic (pure dict-filter), so we
    # reuse it here. Without this wire-up, a future caller invoking
    # `emit_generic("mcp_canonical_guard_blocked", raw_secret=...)`
    # would persist forbidden fields verbatim — Codex R5-02 PoC.
    elif action == "mcp_canonical_guard_allowed":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_allowed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "mcp_canonical_guard_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_canonical_guard_blocked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-071 / ADR-104 — task-route + reality-ledger advisory events.
    # Reuse allowlist-agnostic _scrub_ceo_boot_event helper.
    elif action == "task_route_advised":
        event, dropped = _scrub_ceo_boot_event(
            event, _TASK_ROUTE_ADVISED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
            # PLAN-114 F-1-1.8-47dba028 — wire the typed defense-in-depth
            # action so the strip is in the HMAC-covered audit trail (not
            # only the errors-sidecar breadcrumb). Fail-open: a wire error
            # must never block the parent task_route_advised emit.
            try:
                emit_task_route_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    reason_code="allowlist_strip",
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass
    # PLAN-101 Wave B / ADR-104-AMEND-1 §E — task_route_ground_truth_label.
    elif action == "task_route_ground_truth_label":
        event, dropped = _scrub_ceo_boot_event(
            event, _TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic task_route_ground_truth_label dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §A — cost_envelope_capped.
    elif action == "cost_envelope_capped":
        event, dropped = _scrub_ceo_boot_event(
            event, _COST_ENVELOPE_CAPPED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic cost_envelope_capped dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §B — swarm_runaway_suspected.
    elif action == "swarm_runaway_suspected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_RUNAWAY_SUSPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_runaway_suspected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave A / ADR-133 §C — swarm_paused_owner_absent.
    elif action == "swarm_paused_owner_absent":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST
        )
        # PLAN-136 W3 (S3) — defense-in-depth int coercion of the bucketed
        # loop_duration_hours field (same class as PLAN-135-FOLLOWUP-2 / S234:
        # the HMAC canonical encoder rejects float — S181). The live producer is
        # already int (>=1h bucket), so this path is safe today; this is the
        # authoritative int-coercion boundary so a DIRECT emit_generic caller
        # cannot smuggle a float / string / non-finite into the signed chain.
        # Floor is max(1, ...) — the producer's >=1h bucket floor IS the sentinel
        # (a coerce-failure or sub-1h value collapses to the smallest legit
        # bucket, never 0). OverflowError (int(round(float('inf')))) is caught
        # alongside Type/ValueError so the boundary never raises.
        if (
            "loop_duration_hours" in event
            and event.get("loop_duration_hours") is not None
        ):
            try:
                event["loop_duration_hours"] = max(
                    1, min(int(round(float(event.get("loop_duration_hours")))), 100000)
                )
            except (TypeError, ValueError, OverflowError):
                event["loop_duration_hours"] = 1
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_paused_owner_absent dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — swarm_layer_3_4_blocked.
    elif action == "swarm_layer_3_4_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _SWARM_LAYER_3_4_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic swarm_layer_3_4_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave B / ADR-133 §D — execution_context_signed.
    elif action == "execution_context_signed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_SIGNED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_signed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-102 Wave B / ADR-133 §D — execution_context_validation_failed.
    elif action == "execution_context_validation_failed":
        event, dropped = _scrub_ceo_boot_event(
            event, _EXECUTION_CONTEXT_VALIDATION_FAILED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic execution_context_validation_failed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "reality_ledger_finding":
        event, dropped = _scrub_ceo_boot_event(
            event, _REALITY_LEDGER_FINDING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic reality_ledger_finding dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
            # PLAN-114 F-1-1.8-8d4e2519 — wire the typed defense-in-depth
            # action into the HMAC-covered audit trail. Fail-open.
            try:
                emit_reality_ledger_key_dropped(
                    key=sorted(dropped)[0] if dropped else "",
                    detector=str(event.get("detector", "")),
                    session_id=str(event.get("session_id", "")),
                    project=str(event.get("project", "")),
                )
            except Exception:  # pragma: no cover — audit is fail-open
                pass
    # PLAN-078 Wave 1 — model_routing_advised dispatch gate.
    elif action == "model_routing_advised":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_ADVISED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-persona-routing-wire W2 — model_routing_enforced gate.
    elif action == "model_routing_enforced":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_ENFORCED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_enforced dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-persona-routing-wire W2 — model_routing_eval_error gate.
    elif action == "model_routing_eval_error":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_ROUTING_EVAL_ERROR_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic model_routing_eval_error dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-078 Wave 2 — estimate_drift dispatch gates.
    elif action == "estimate_drift_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "estimate_drift_systematic_bias":
        event, dropped = _scrub_ceo_boot_event(
            event, _ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_drift_systematic_bias dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-078 Wave 5 — ceo_boot_task_candidate_emitted dispatch gate.
    # Defense-in-depth: blocks future direct callers (e.g.
    # `emit_generic("ceo_boot_task_candidate_emitted", subject="...")`)
    # from leaking subject text or other forbidden fields.
    elif action == "ceo_boot_task_candidate_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic ceo_boot_task_candidate_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 1-full — pair_rail_codex_injection_detected dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through the
    # Sec MF-3 allowlist scrub. Raw matched-content / raw-offset must NEVER
    # persist (LLM06 side-channel guard).
    elif action == "pair_rail_codex_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_CODEX_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_codex_injection_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 2 — dispatcher_route dispatch gate.
    # Defense-in-depth: archetype profile / task description / skill body
    # MUST never persist via this action — the canonical sources are
    # _CANONICAL_GUARDS-protected. Only routing-decision metadata + perf
    # field (wall_clock_s) per allowlist.
    elif action == "dispatcher_route":
        event, dropped = _scrub_ceo_boot_event(
            event, _DISPATCHER_ROUTE_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic dispatcher_route dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 3 — pair_rail_case dispatch gate.
    elif action == "pair_rail_case":
        # PLAN-161 C5 r5 F2 + r6 F2 — VALUE re-coercion for the new
        # `review_id` correlation field (exact-16-hex-or-"" gate on the
        # RAW value; mirrors the `file_path_hash_prefix` gate on
        # `pair_rail_review_expected`): closes the direct emit_generic
        # caller path so an off-shape value (free text, oversize, raw
        # path) can never reach the signed chain — off-shape -> ""
        # (dropped, never truncated).
        _prc_rid = event.get("review_id")
        if not (isinstance(_prc_rid, str)
                and _PAIR_RAIL_REVIEW_ID_RE.fullmatch(_prc_rid)):
            event["review_id"] = ""
        # ADR-110-AMEND-2 §1.6 — VALUE re-coercion for the effective-budget
        # field: bounded INTEGER milliseconds. A direct emit_generic caller
        # passing float seconds (the shape the amendment prose names) would
        # otherwise trip the canonical_json no-float invariant and the spool
        # writer would DROP the whole case row — manufacturing the /ceo-boot
        # S254 liveness deficit this action exists to disprove.
        if "timeout_ms" in event:
            event["timeout_ms"] = _coerce_pair_rail_timeout_ms(
                event["timeout_ms"]
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_CASE_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_case dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-081 Phase 4 — pair_rail_promotion dispatch gate.
    elif action == "pair_rail_promotion":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_PROMOTION_EMIT_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_promotion dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.4 (S106) — token_budget_guard_paused dispatch gate.
    elif action == "token_budget_guard_paused":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic token_budget_guard_paused dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_block dispatch gate.
    elif action == "anti_ceo_overhead_block":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_block dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_override_used dispatch gate.
    elif action == "anti_ceo_overhead_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic anti_ceo_overhead_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 0b sub-agent 0.7d (S106) — smart_loading_resolved dispatch gate.
    elif action == "smart_loading_resolved":
        event, dropped = _scrub_ceo_boot_event(
            event, _SMART_LOADING_RESOLVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic smart_loading_resolved dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.1 — first_run_wizard_completed dispatch gate.
    elif action == "first_run_wizard_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_completed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.2 — contextual_recommendation_emitted dispatch gate.
    elif action == "contextual_recommendation_emitted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic contextual_recommendation_emitted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.4 — value_dashboard_summarized dispatch gate.
    elif action == "value_dashboard_summarized":
        event, dropped = _scrub_ceo_boot_event(
            event, _VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic value_dashboard_summarized dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_write_override_used dispatch gate.
    # PLAN-085 Wave C.1 — live_adapter_blocked dispatch gate.
    elif action == "live_adapter_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _LIVE_ADAPTER_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic live_adapter_blocked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — prompt_injection_detected dispatch gate.
    elif action == "prompt_injection_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _PROMPT_INJECTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic prompt_injection_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex B3 P1 — mcp_injection_finding scrub gate (was passthrough).
    # MCP-controlled snippet_preview is re-truncated via _preview() so a direct
    # emit_generic caller cannot bypass the named-emitter [:120] cap.
    elif action == "mcp_injection_finding":
        if "snippet_preview" in event:
            event["snippet_preview"] = _preview(
                str(event.get("snippet_preview", "")), max_len=120
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_INJECTION_FINDING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_injection_finding dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — secret_leak_detected dispatch gate.
    elif action == "secret_leak_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SECRET_LEAK_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic secret_leak_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — pii_redacted_outgoing dispatch gate.
    elif action == "pii_redacted_outgoing":
        event, dropped = _scrub_ceo_boot_event(
            event, _PII_REDACTED_OUTGOING_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic pii_redacted_outgoing dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave G.1b — codex_egress_redacted dispatch gate.
    elif action == "codex_egress_redacted":
        event, dropped = _scrub_ceo_boot_event(
            event, _CODEX_EGRESS_REDACTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic codex_egress_redacted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-112-FOLLOWUP-codex-egress-proof-telemetry — pair_rail_outgoing_redaction_applied gate.
    elif action == "pair_rail_outgoing_redaction_applied":
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic pair_rail_outgoing_redaction_applied dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave E.4 piggyback — canonical_edit_completed dispatch gate.
    elif action == "canonical_edit_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CANONICAL_EDIT_COMPLETED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic canonical_edit_completed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.2 — credential_blocked_due_to_age dispatch gate.
    elif action == "credential_blocked_due_to_age":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_BLOCKED_DUE_TO_AGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic credential_blocked_due_to_age dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.2 — credential_emergency_override_used dispatch gate.
    elif action == "credential_emergency_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_EMERGENCY_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic credential_emergency_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-117 WS-A — credential_override_late_set_ignored dispatch gate.
    elif action == "credential_override_late_set_ignored":
        event, dropped = _scrub_ceo_boot_event(
            event, _CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST
        )
        # Self-enforce the closed-enum / no-value-echo contract at the chokepoint,
        # independent of the caller: FORCE the var name to the constant and COERCE
        # an out-of-enum provenance hint. The rejected override VALUE can never
        # reach the payload via either field (even on a direct emit_generic call).
        event["attempted_var_name"] = _CREDENTIAL_OVERRIDE_VAR_NAME
        if event.get("provenance_hint") not in _CREDENTIAL_OVERRIDE_PROVENANCE_HINTS:
            event["provenance_hint"] = "unspecified"
        if dropped:
            _breadcrumb(
                "emit_generic credential_override_late_set_ignored dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.3 — mcp_bearer_replay_rejected dispatch gate.
    elif action == "mcp_bearer_replay_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_BEARER_REPLAY_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_bearer_replay_rejected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-085 Wave C.3 — mcp_non_loopback_rejected dispatch gate.
    elif action == "mcp_non_loopback_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _MCP_NON_LOOPBACK_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                "emit_generic mcp_non_loopback_rejected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "trading_write_override_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_WRITE_OVERRIDE_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_write_override_used dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_invoked dispatch gate.
    elif action == "trading_kill_switch_invoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_INVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_invoked dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_disabled dispatch gate.
    elif action == "trading_kill_switch_disabled":
        event, dropped = _scrub_ceo_boot_event(
            event, _TRADING_KILL_SWITCH_DISABLED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic trading_kill_switch_disabled dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-088 canonical-13 god-mode auto-activation (S114) — 12 dispatch
    # gates for the 11 net-new + 1 wire (mcp_route_advised). Sec MF-3
    # defense-in-depth per qa-architect P0-3: prevent emit_generic callers
    # from bypassing the typed-wrapper allowlist enforcement.
    elif action == "cache_discipline_alerted":
        event, dropped = _scrub_ceo_boot_event(event, _CACHE_DISCIPLINE_ALERTED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic cache_discipline_alerted dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "first_run_wizard_dispatched":
        event, dropped = _scrub_ceo_boot_event(event, _FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic first_run_wizard_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "estimate_calibrator_pipeline_run":
        event, dropped = _scrub_ceo_boot_event(event, _ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic estimate_calibrator_pipeline_run dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "subagent_findings_partial_drop":
        event, dropped = _scrub_ceo_boot_event(event, _SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic subagent_findings_partial_drop dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-106 Wave H.1 — output_scan_finding_suppressed dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through
    # the Sec MF-3 allowlist scrub. NO raw secret / matched_content /
    # command body must persist — closed-enum `pattern_id` + `family`
    # enforced at producer site (`_lib/output_scan._PATTERN_IDS`).
    elif action == "output_scan_finding_suppressed":
        event, dropped = _scrub_ceo_boot_event(
            event, _OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic output_scan_finding_suppressed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "anthropic_429_observed":
        event, dropped = _scrub_ceo_boot_event(event, _ANTHROPIC_429_OBSERVED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic anthropic_429_observed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "git_index_lock_retry":
        event, dropped = _scrub_ceo_boot_event(event, _GIT_INDEX_LOCK_RETRY_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic git_index_lock_retry dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "codex_invoke_dispatched":
        # PLAN-143 item-3 (audit-errors-04): clamp the dual-rail exit_code
        # to the POSIX exit-status range (0..255) BEFORE the allowlist
        # scrub so the now-retained field can never carry an unbounded /
        # non-int value. Mirrors the bps/count clamps used elsewhere in
        # emit_generic. Absent/garbage -> 0 (fail-open, advisory telemetry).
        if "exit_code" in event:
            try:
                event["exit_code"] = max(0, min(255, int(event["exit_code"])))
            except (TypeError, ValueError):
                event["exit_code"] = 0
        event, dropped = _scrub_ceo_boot_event(event, _CODEX_INVOKE_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic codex_invoke_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "tier_policy_misrouting_advised":
        event, dropped = _scrub_ceo_boot_event(event, _TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic tier_policy_misrouting_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "tier_policy_loader_fallback_observed":  # PLAN-116 (S172)
        # Closed-enum validation BEFORE scrub (deny-by-default; mirrors
        # persona_coverage_synthesized). An out-of-enum reason_code drops the
        # whole event with a breadcrumb so a buggy/future caller cannot
        # pollute the action with free text.
        _rc = str(event.get("reason_code", ""))
        if _rc not in _TIER_POLICY_LOADER_FALLBACK_REASON_CODES:
            # Do NOT echo the rejected value: free-text into the errors
            # sidecar is exactly the noise class PLAN-116 closes. Length only.
            _breadcrumb(
                "emit_generic tier_policy_loader_fallback_observed dropped: "
                f"reason_code not in closed enum (len={len(_rc)})"
            )
            return
        event, dropped = _scrub_ceo_boot_event(
            event, _TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic tier_policy_loader_fallback_observed dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "audit_producer_path_pollution_detected":  # PLAN-118 AC-B5
        # Closed-enum validation BEFORE scrub. Two enums: `chokepoint`
        # (origin of the breadcrumb) + `reason_code` (which canonical
        # module mismatched). NO `__file__` echo — only sha256[:8]
        # prefixes per [[feedback-closed-enum-breadcrumb-must-not-echo-
        # rejected-value]]. Out-of-enum values DROP the event with a
        # length-only breadcrumb (defense against a buggy/future caller
        # smuggling free text). Sec MF-3 defense-in-depth: a direct
        # emit_generic caller cannot bypass the typed wrapper's
        # validation.
        _cp = str(event.get("chokepoint", ""))
        if _cp not in _AUDIT_PRODUCER_PATH_POLLUTION_CHOKEPOINTS:
            _breadcrumb(
                "emit_generic audit_producer_path_pollution_detected dropped: "
                f"chokepoint not in closed enum (len={len(_cp)})"
            )
            return
        _rc = str(event.get("reason_code", ""))
        if _rc not in _AUDIT_PRODUCER_PATH_POLLUTION_REASON_CODES:
            _breadcrumb(
                "emit_generic audit_producer_path_pollution_detected dropped: "
                f"reason_code not in closed enum (len={len(_rc)})"
            )
            return
        # Validate the two 8-hex-prefix fields exist and are well-formed.
        for _hex_field in ("path_sha256_prefix", "expected_canonical_prefix"):
            _val = str(event.get(_hex_field, ""))
            if len(_val) != 8 or not all(c in "0123456789abcdef" for c in _val):
                _breadcrumb(
                    "emit_generic audit_producer_path_pollution_detected dropped: "
                    f"{_hex_field} not 8 hex chars (len={len(_val)})"
                )
                return
        event, dropped = _scrub_ceo_boot_event(
            event, _AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic audit_producer_path_pollution_detected dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "mcp_route_advised":
        event, dropped = _scrub_ceo_boot_event(event, _MCP_ROUTE_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic mcp_route_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "cookbook_pattern_advised":
        event, dropped = _scrub_ceo_boot_event(event, _COOKBOOK_PATTERN_ADVISED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic cookbook_pattern_advised dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "pair_rail_phase_advanced":
        event, dropped = _scrub_ceo_boot_event(event, _PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic pair_rail_phase_advanced dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    elif action == "batch_dispatched":
        event, dropped = _scrub_ceo_boot_event(event, _BATCH_DISPATCHED_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic batch_dispatched dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-107 Wave B.4.2 (S145 2026-05-19) — stdlib_violation dispatch gate.
    # Defense-in-depth: any direct emit_generic caller is routed through
    # the Sec MF-3 allowlist scrub. Without this branch the orphan event
    # would be silently scrubbed by the default fall-through path.
    elif action == "stdlib_violation":
        event, dropped = _scrub_ceo_boot_event(event, _STDLIB_VIOLATION_ALLOWLIST)
        if dropped:
            _breadcrumb(
                f"emit_generic stdlib_violation dropped forbidden field(s): "
                f"{sorted(dropped)[:10]}"
            )
    # PLAN-113 Phase B B-STRUCTURAL — federation_* dispatch gates. Each LIVE
    # federation action (emitted via _lib.federation.*._safe_emit ->
    # emit_generic) is routed through the Sec MF-3 allowlist scrub. Without
    # these branches the caller kwargs were written VERBATIM into the HMAC
    # audit log (the ghost-action leak). The two path fields (source_path /
    # sentinel_path) are re-hashed to 12-hex AFTER the scrub so no host path
    # can leak even from an in-allowlist field.
    elif action == "federation_connection_accepted":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_ACCEPTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_accepted dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_connection_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_rejected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_connection_replay_suspected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CONNECTION_REPLAY_SUSPECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_connection_replay_suspected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_expiry_warned":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_EXPIRY_WARNED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_expiry_warned dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_revoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_REVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_revoked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_cert_validity_window_too_large":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_CERT_VALIDITY_WINDOW_TOO_LARGE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_cert_validity_window_too_large "
                f"dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_enable_sentinel_invalid":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_ENABLE_SENTINEL_INVALID_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_enable_sentinel_invalid dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_lan_bind_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_LAN_BIND_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_lan_bind_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_attempt_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_ATTEMPT_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_attempt_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_endpoint_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_ENDPOINT_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_endpoint_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_write_disabled_sentinel_invalid":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_WRITE_DISABLED_SENTINEL_INVALID_ALLOWLIST
        )
        if "sentinel_path" in event:
            event["sentinel_path"] = _federation_safe_path_hash(
                event.get("sentinel_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_write_disabled_sentinel_invalid "
                f"dropped forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_scope_denied":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_SCOPE_DENIED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_scope_denied dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_event_action_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_EVENT_ACTION_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_event_action_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_event_pushed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_EVENT_PUSHED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_event_pushed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_event_pushed_batch":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_EVENT_PUSHED_BATCH_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_event_pushed_batch dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_registered":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REGISTERED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_registered dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_registered_collision":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REGISTERED_COLLISION_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_registered_collision dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_revoked_remote":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_REVOKED_REMOTE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_revoked_remote dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_invalid_no_fingerprint":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_INVALID_NO_FINGERPRINT_ALLOWLIST
        )
        if "source_path" in event:
            event["source_path"] = _federation_safe_path_hash(
                event.get("source_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_invalid_no_fingerprint dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_peer_list_reloaded":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PEER_LIST_RELOADED_ALLOWLIST
        )
        if "source_path" in event:
            event["source_path"] = _federation_safe_path_hash(
                event.get("source_path", "")
            )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_peer_list_reloaded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_pin_legacy_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_PIN_LEGACY_USED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_pin_legacy_used dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_spki_fingerprint_mismatch":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_SPKI_FINGERPRINT_MISMATCH_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_spki_fingerprint_mismatch dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_message_storm_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_MESSAGE_STORM_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_message_storm_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_audit_log_backpressure":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUDIT_LOG_BACKPRESSURE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_audit_log_backpressure dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_tamper_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_TAMPER_DETECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_tamper_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Phase B B5 — defense-in-depth scrub branches for the
    # RESERVED-no-producer destructive federation actions. No producer
    # invokes these today (see _RESERVED_ACTIONS), but if an accidental
    # caller ever appears the fields are allowlist-bounded, not raw.
    elif action == "federation_autonomous_call_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_AUTONOMOUS_CALL_BLOCKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_autonomous_call_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_hmac_secret_rotated":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_HMAC_SECRET_ROTATED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_hmac_secret_rotated dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_key_floor_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_KEY_FLOOR_REJECTED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_key_floor_rejected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    elif action == "federation_key_floor_stale":
        event, dropped = _scrub_ceo_boot_event(
            event, _FEDERATION_KEY_FLOOR_STALE_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic federation_key_floor_stale dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P1 — bash_canonical_bypass_invoked Sec MF-3 scrub.
    # target_path_preview (raw filesystem path) replaced by target_path_hash
    # (12-hex sha256 prefix). The allowlist enforces the deny-by-default
    # boundary so no future caller can reintroduce a raw path field.
    elif action == "bash_canonical_bypass_invoked":
        event, dropped = _scrub_ceo_boot_event(
            event, _BASH_CANONICAL_BYPASS_INVOKED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic bash_canonical_bypass_invoked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P2 — spawn_confidence_advisory explicit allowlist branch.
    # Moved from _EMIT_GENERIC_PASSTHROUGH; Sec MF-3 deny-by-default enforced.
    elif action == "spawn_confidence_advisory":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic spawn_confidence_advisory dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-153 Wave E item 7 (ADR-175) — spawn_prompt_defense_gate Sec MF-3 scrub.
    # Dedicated deny-by-default branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS any non-allowlisted key; the value re-coercion below
    # closes the direct-emit_generic-caller path (bypassing the typed producer):
    # present/enforced collapse to 0/1 flags and keyword is string-coerced + 32-
    # char capped, so no prompt/description body can ride the closed-enum channel.
    elif action == "spawn_prompt_defense_gate":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPAWN_PROMPT_DEFENSE_GATE_ALLOWLIST
        )
        event["keyword"] = str(event.get("keyword", ""))[:32]
        event["present"] = 1 if str(event.get("present")) in ("1", "True", "true") else 0
        event["enforced"] = 1 if str(event.get("enforced")) in ("1", "True", "true") else 0
        if dropped:
            _breadcrumb(
                f"emit_generic spawn_prompt_defense_gate dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-113 Codex P2 — spec_context_sanitized explicit allowlist branch.
    # Moved from _EMIT_GENERIC_PASSTHROUGH; Sec MF-3 deny-by-default enforced.
    elif action == "spec_context_sanitized":
        event, dropped = _scrub_ceo_boot_event(
            event, _SPEC_CONTEXT_SANITIZED_ALLOWLIST
        )
        if dropped:
            _breadcrumb(
                f"emit_generic spec_context_sanitized dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A2 — invisible-unicode hard-block breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted
    # keys (so a smuggled prompt/content/char body can never reach the wire) and the
    # VALUE re-coercion below closes the direct-emit_generic-caller path: a raw value
    # placed in unicode_class/surface is reset to a safe default, and char_count is
    # clamped to a bounded non-negative int.
    elif action == "invisible_unicode_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _INVISIBLE_UNICODE_BLOCKED_ALLOWLIST
        )
        if event.get("unicode_class") not in _INVISIBLE_UNICODE_CLASSES:
            event["unicode_class"] = "control"
        if event.get("surface") not in _INVISIBLE_UNICODE_SURFACES:
            event["surface"] = "spawn"
        # Bounded non-negative int (no float in HMAC-covered fields; clamp 0..1e6).
        try:
            cc = int(event.get("char_count", 0))
        except (TypeError, ValueError):
            cc = 0
        event["char_count"] = max(0, min(cc, 1_000_000))
        # enforced is a 0/1 flag.
        event["enforced"] = 1 if str(event.get("enforced")) in ("1", "True", "true") else 0
        if dropped:
            _breadcrumb(
                f"emit_generic invisible_unicode_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-125 WS-1 — per-tool-call lifecycle telemetry. Dedicated scrub
    # branch (Sec MF-SEC-2: NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name
    # scrub below only DROPS non-allowlisted keys — it does NOT re-validate the
    # VALUES of the allowlisted enum fields. So a direct emit_generic caller
    # (bypassing the typed emitter) could otherwise smuggle a raw mcp__* tool
    # name or a raw duration token into the signed chain via the allowed
    # tool_name_enum / duration_bucket fields. Re-coerce both VALUES here by
    # closed-set membership — mirroring emit_tool_call_lifecycle_recorded — so
    # the emit_generic path is a true second line of defense (MF-SEC-1/3).
    elif action == "tool_call_lifecycle_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST
        )
        if event.get("tool_name_enum") not in _TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("duration_bucket") not in _TOOL_CALL_LIFECYCLE_DURATION_BUCKETS:
            event["duration_bucket"] = "lt_100ms"
        # The allowlist also permits success / orphan — coerce their VALUES to
        # bool too (Codex pair-rail P0): a direct emit_generic caller could
        # otherwise put a free-form string/dict (signed verbatim into the HMAC
        # chain) or a float (breaks canonical-JSON → unsigned hmac_error row)
        # into either field. The typed emitter already does bool(...); mirror it.
        event["success"] = bool(event.get("success"))
        event["orphan"] = bool(event.get("orphan"))
        if dropped:
            _breadcrumb(
                f"emit_generic tool_call_lifecycle_recorded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-124 WS-1 — git hook-bypass guard breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH;
    # [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # field-name scrub below only DROPS non-allowlisted keys (so a smuggled
    # `command`/`raw`/`token` body never reaches the wire) — it does NOT
    # re-validate the VALUE of the allowed `flag_class` field. So a direct
    # emit_generic caller (bypassing the typed emitter) could otherwise put a
    # raw command substring into `flag_class` and have it signed verbatim into
    # the HMAC chain. Re-coerce the VALUE here by closed-set membership —
    # mirroring emit_git_hook_bypass_blocked — so the emit_generic path is a
    # true second line of defense (MF-G).
    elif action == "git_hook_bypass_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST
        )
        if event.get("flag_class") not in _GIT_HOOK_BYPASS_FLAG_CLASSES:
            event["flag_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic git_hook_bypass_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A1 — env-hijack denylist breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`key`/`value` body never reaches the wire) and the
    # VALUE re-coercion below closes the direct-emit_generic-caller path: a raw
    # var name/value placed in `hijack_class` is reset to "parse_failure".
    elif action == "env_var_hijack_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST
        )
        if event.get("hijack_class") not in _ENV_VAR_HIJACK_CLASSES:
            event["hijack_class"] = "parse_failure"
        if dropped:
            _breadcrumb(
                f"emit_generic env_var_hijack_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 A3 — egress-destination breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`url`/`full_url` body never reaches the wire); the
    # egress_class re-coercion resets an out-of-set value; the destination is
    # re-reduced to a bare host (defense-in-depth on a direct emit_generic caller).
    elif action == "egress_destination_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _EGRESS_DESTINATION_DETECTED_ALLOWLIST
        )
        if event.get("egress_class") not in _EGRESS_CLASSES:
            event["egress_class"] = "unknown"
        if "destination" in event:
            event["destination"] = _coerce_egress_destination(event["destination"])
        if dropped:
            _breadcrumb(
                f"emit_generic egress_destination_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 E1 — adversary local-rules breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted keys
    # (so a smuggled `command`/`match`/`regex` body never reaches the wire); the
    # closed-enum re-coercions below close the direct-emit_generic-caller path.
    elif action == "adversary_review_flagged":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
        )
        if event.get("decision") not in _ADVERSARY_DECISIONS:
            event["decision"] = "advisory"
        if event.get("rule_class") not in _ADVERSARY_RULE_CLASSES:
            event["rule_class"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic adversary_review_flagged dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 G1 — persistent-instructions breadcrumb. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS
    # non-allowlisted keys (so a smuggled instruction body / matched line / path
    # never reaches the wire); the closed-enum re-coercion closes the direct
    # emit_generic-caller path.
    elif action == "persistent_instructions_blocked":
        event, dropped = _scrub_ceo_boot_event(
            event, _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST
        )
        if event.get("reason") not in _PERSISTENT_INSTRUCTIONS_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic persistent_instructions_blocked dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-133 G3 — hint provenance breadcrumb. Dedicated scrub branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS non-allowlisted
    # keys (so a smuggled hint body / matched line / path text never reaches the
    # wire); the closed-enum re-coercion closes the direct emit_generic-caller
    # path.
    elif action == "hint_provenance_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _HINT_PROVENANCE_RECORDED_ALLOWLIST
        )
        if event.get("reason") not in _HINT_PROVENANCE_REASONS:
            event["reason"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic hint_provenance_recorded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W1 S3 — /ceo-boot settings/env tamper tripwire breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys (so a smuggled finding
    # `detail` / env value / endpoint URL never reaches the wire); the
    # closed-enum re-coercions + int clamp close the direct
    # emit_generic-caller path (S172 doctrine — rejected values are
    # replaced with the safe sentinel, never echoed).
    elif action == "settings_tamper_detected":
        event, dropped = _scrub_ceo_boot_event(
            event, _SETTINGS_TAMPER_DETECTED_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _SETTINGS_TAMPER_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(
                0, min(99, int(event.get("finding_count", 0)))
            )
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic settings_tamper_detected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-174 W1 (registered by the SENT-S318 pack) — ceremony-lint ADR-186
    # unlock breadcrumb. The emitter shipped in 7d467a8 WITHOUT this registry
    # half and was parked in 908707e ("um emissor nao embarca antes do
    # registro dele"); this branch is the registration that un-parks it.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys (so a smuggled unlock
    # REASON text / file path / script body never reaches the wire); the
    # shape checks close the direct emit_generic-caller path (S172 doctrine
    # — rejected values are replaced with the safe sentinel, never echoed).
    elif action == "ceremony_lint_unlock_used":
        event, dropped = _scrub_ceo_boot_event(
            event, _CEREMONY_LINT_UNLOCK_USED_ALLOWLIST
        )
        fs = event.get("file_sha256")
        if not (
            isinstance(fs, str)
            and len(fs) == 16
            and all(c in "0123456789abcdef" for c in fs)
        ):
            # 16-hex sha256 PREFIX of the unlocked ceremony script — a
            # malformed value is coerced to the sentinel, never echoed.
            event["file_sha256"] = "invalid"
        rl = event.get("reason_len", 0)
        if isinstance(rl, bool) or not isinstance(rl, int):
            # TYPE-strict like _context_pressure_bucket_ok: bool is an int
            # subclass and a float would make canonical_json drop the WHOLE
            # event to an audit-log.errors breadcrumb (S181 class).
            event["reason_len"] = 0
        else:
            event["reason_len"] = max(0, min(9999, rl))
        if dropped:
            _breadcrumb(
                f"emit_generic ceremony_lint_unlock_used dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-182 W1 (ADR-079 S318 amendment §2) — salt mint register.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys, so a slug, salt path or
    # salt value SMUGGLED IN UNDER A KEY THIS ACTION DOES NOT DECLARE never
    # reaches the wire; closed-enum + shape coercion closes the direct
    # emit_generic-caller path (S172 doctrine — rejected values are
    # replaced with the safe sentinel, never echoed).
    #
    # rc.1 re-pass part 6 C5 — the sentence above used to read "a smuggled
    # slug/path/salt value never reaches the wire" without saying WHICH
    # keys, which a reader takes as a claim that no path is ever emitted
    # here. `project` is an ALLOWLISTED base field required of every
    # registered line (SPEC/v1/audit-log.schema.md), and it carries the
    # repository path on this action exactly as it does on every other one,
    # in this version and in v1.3.0. The scrub is about UNDECLARED keys;
    # it is not, and never was, a promise that the event carries no path.
    elif action == "salt_rotation_registered":
        event, dropped = _scrub_ceo_boot_event(
            event, _SALT_ROTATION_REGISTERED_ALLOWLIST
        )
        # rail r13 P2-6: type-check ANTES do teste de pertinencia — um
        # list/dict de chamador direto levantaria TypeError no frozenset
        # e quebraria o contrato never-raises do emit_generic.
        _reason = event.get("reason")
        if not isinstance(_reason, str) or _reason not in _SALT_ROTATION_REASONS:
            event["reason"] = "other"
        # salt_scope is a fixed vocabulary of one today ("project", the
        # ADR-079 S318 unit); anything else is coerced, never echoed.
        if event.get("salt_scope") != "project":
            event["salt_scope"] = "project"
        ss = event.get("slug_sha256")
        if not (
            isinstance(ss, str)
            and len(ss) == 16
            and all(c in "0123456789abcdef" for c in ss)
        ):
            # 16-hex sha256 PREFIX of the native slug — a malformed
            # value is coerced to the sentinel, never echoed.
            event["slug_sha256"] = "invalid"
        if dropped:
            _breadcrumb(
                f"emit_generic salt_rotation_registered dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H2 — ConfigChange-guard observed breadcrumb. Dedicated
    # scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name scrub
    # DROPS non-allowlisted keys (so a smuggled file path / settings body /
    # key value never reaches the wire); the closed-enum re-coercion closes
    # the direct emit_generic-caller path (S172 doctrine — rejected values
    # are replaced with the safe sentinel, never echoed).
    elif action == "config_change_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIG_CHANGE_OBSERVED_ALLOWLIST
        )
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H2 — ConfigChange-guard forbidden-key breadcrumb (the
    # advisory-block path). Same contract as settings_tamper_detected: the
    # field-name scrub DROPS non-allowlisted keys, closed-enum re-coercions
    # + int clamp close the direct emit_generic-caller path. The forbidden
    # key's VALUE and the finding DETAIL never reach the wire.
    elif action == "config_change_forbidden_key":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST
        )
        if event.get("tamper_class") not in _SETTINGS_TAMPER_CLASSES:
            event["tamper_class"] = "other"
        if event.get("layer") not in _CONFIG_CHANGE_LAYERS:
            event["layer"] = "other"
        try:
            event["finding_count"] = max(
                0, min(99, int(event.get("finding_count", 0)))
            )
        except (TypeError, ValueError):
            event["finding_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic config_change_forbidden_key dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H1 (ADR-153) — PreCompact compaction-continuity snapshot
    # breadcrumb. Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH).
    # The field-name scrub DROPS non-allowlisted keys (so a smuggled
    # snapshot body / plan text / hmac hex never reaches the wire); the
    # closed-enum re-coercions + strict plan-id shape check + int clamp
    # close the direct emit_generic-caller path (S172 doctrine — rejected
    # values are replaced with the safe sentinel, never echoed).
    elif action == "compaction_continuity_snapshot":
        event, dropped = _scrub_ceo_boot_event(
            event, _COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST
        )
        if event.get("trigger") not in _COMPACTION_TRIGGERS:
            event["trigger"] = "other"
        if event.get("snapshot_outcome") not in _COMPACTION_SNAPSHOT_OUTCOMES:
            event["snapshot_outcome"] = "other"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        try:
            event["chain_length"] = max(
                0, min(99999999, int(event.get("chain_length", 0)))
            )
        except (TypeError, ValueError):
            event["chain_length"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic compaction_continuity_snapshot dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H1 (ADR-153) — PostCompact governance-pointer reinjection
    # breadcrumb. Same contract: deny-by-default scrub, strict plan-id shape
    # check, bool/int coercions. The reinjected additionalContext TEXT is
    # never an allowed field (pointers-only doctrine — the wire carries
    # counters, not context).
    elif action == "compaction_context_reinjected":
        event, dropped = _scrub_ceo_boot_event(
            event, _COMPACTION_CONTEXT_REINJECTED_ALLOWLIST
        )
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        if not isinstance(event.get("snapshot_found"), bool):
            event["snapshot_found"] = False
        try:
            event["snapshot_age_s"] = max(
                0, min(9999999, int(event.get("snapshot_age_s", 0)))
            )
        except (TypeError, ValueError):
            event["snapshot_age_s"] = 0
        try:
            event["pointer_count"] = max(
                0, min(9, int(event.get("pointer_count", 0)))
            )
        except (TypeError, ValueError):
            event["pointer_count"] = 0
        # PLAN-179 W1-b — same clamp discipline for the constraint counter.
        # int(), never float: a float here is refused by canonical_json and
        # takes the WHOLE event down (S181/ADR-055-AMEND-2). Absent key means
        # a producer that predates pinning, so the honest value is 0.
        try:
            event["constraint_count"] = max(
                0, min(99, int(event.get("constraint_count", 0)))
            )
        except (TypeError, ValueError):
            event["constraint_count"] = 0
        if dropped:
            _breadcrumb(
                f"emit_generic compaction_context_reinjected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-179 W0 US2 (amendment 8.1) — EDGE-TRIGGERED context-pressure
    # breadcrumb. Same deny-by-default contract as the compaction pair
    # above (this is the ADR-153 successor rail, so it reuses the SAME
    # scrub helper and the SAME strict plan-id validator): the field-name
    # scrub DROPS non-allowlisted keys, then the closed-enum re-coercions
    # close the direct emit_generic-caller path (S172 doctrine — rejected
    # values are replaced with the safe sentinel, never echoed). The
    # used_bucket coercion is TYPE-strict on purpose: a float that merely
    # COMPARES equal to a bucket would be refused by canonical_json and
    # take the whole event down with it (S181/ADR-055-AMEND-2).
    elif action == "context_pressure_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _CONTEXT_PRESSURE_OBSERVED_ALLOWLIST
        )
        if not _context_pressure_bucket_ok(event.get("used_bucket")):
            # 0 = "unrecognized / absent bucket", deliberately OUTSIDE the
            # {40,60,80,90,95} percent enum so a consumer can always tell a
            # real rung from a coerced one. Already TYPE-safe: the helper
            # isinstance-checks before any membership test (see below).
            event["used_bucket"] = 0
        # PLAN-179 rail finding B (round-1 REJECT) — isinstance-guard FIRST.
        # `x in frozenset` raises TypeError when x is UNHASHABLE (a list or a
        # dict from a direct/future emit_generic caller), and that exception
        # escapes HERE — before _write_event's fail-open wrapper can absorb it
        # — which breaks emit_generic's documented never-raises contract. Same
        # H4 class the PLAN-163 fix-pass closed in `directory_added_recorded`,
        # `notification_lifecycle` and `night_mode_toggled`; this branch is
        # written in that same shape. A non-str value is off-enum by
        # definition → the closed default "other" (S172: never echoed).
        #
        # The two SIBLING coercions in this branch were audited for the same
        # hazard and are already safe: `_context_pressure_bucket_ok` rejects
        # non-int (and bool) BEFORE `value in _CONTEXT_PRESSURE_USED_BUCKETS_PCT`,
        # and `_compaction_plan_id_ok` isinstance-checks str before len()/
        # startswith(). Only `event_source` tested membership on a raw value.
        _cp_src = event.get("event_source")
        if (not isinstance(_cp_src, str)
                or _cp_src not in _CONTEXT_PRESSURE_EVENT_SOURCES):
            event["event_source"] = "other"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        if dropped:
            _breadcrumb(
                f"emit_generic context_pressure_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-179 W2 (ADR-195) — advisory work-boundary ledger observation.
    # Dedicated deny-by-default branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys, so a smuggled commit
    # message / committed path / ledger body never reaches the wire; the
    # closed-enum + TYPE-strict int coercions then close the direct
    # emit_generic-caller path (S172 doctrine — rejected values are replaced
    # with the safe sentinel, never echoed). Every membership test is
    # isinstance-guarded FIRST: `x in frozenset` raises TypeError when x is
    # UNHASHABLE (a list/dict from a direct caller) and that exception would
    # escape emit_generic's never-raises contract before _write_event's
    # fail-open wrapper could absorb it (PLAN-179 rail finding B / H4 class).
    elif action == "ledger_checkpoint_recorded":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEDGER_CHECKPOINT_RECORDED_ALLOWLIST
        )
        _lc_outcome = event.get("outcome")
        if (not isinstance(_lc_outcome, str)
                or _lc_outcome not in _LEDGER_CHECKPOINT_OUTCOMES):
            event["outcome"] = "other"
        _lc_scope = event.get("scope_source")
        if (not isinstance(_lc_scope, str)
                or _lc_scope not in _LEDGER_CHECKPOINT_SCOPE_SOURCES):
            event["scope_source"] = "other"
        _lc_state = event.get("state_kind")
        if (not isinstance(_lc_state, str)
                or _lc_state not in _LEDGER_CHECKPOINT_STATE_KINDS):
            # "unavailable" (not "other"): the producer's own sentinel for
            # "the observation state could not be read".
            event["state_kind"] = "unavailable"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            # Shared strict PLAN-NNN validator — a path-traversal attempt
            # smuggled through plan_id is rejected, not echoed.
            event["plan_id"] = "unknown"
        for _lc_key, _lc_hi in (
            ("in_scope_path_count", 99),
            ("ledger_size_bucket_kib", 99),
            ("unverified_ac_claim_count", 99),
            ("commits_since_last_observation", 99),
            ("over_ceiling", 1),
            ("would_block", 1),
        ):
            event[_lc_key] = _ledger_int_field(event.get(_lc_key), _lc_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_checkpoint_recorded dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-179 W2 (ADR-195) — the same rail's SKIP row. Same deny-by-default
    # contract as the branch above; `reason` is the producer's closed skip
    # enum and carries no free text, so "why the rail stayed quiet" is
    # countable without ever describing the commit.
    elif action == "ledger_checkpoint_skipped":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST
        )
        _ls_reason = event.get("reason")
        if (not isinstance(_ls_reason, str)
                or _ls_reason not in _LEDGER_CHECKPOINT_SKIP_REASONS):
            event["reason"] = "other"
        _ls_state = event.get("state_kind")
        if (not isinstance(_ls_state, str)
                or _ls_state not in _LEDGER_CHECKPOINT_STATE_KINDS):
            event["state_kind"] = "unavailable"
        if not _compaction_plan_id_ok(event.get("plan_id")):
            event["plan_id"] = "unknown"
        for _ls_key, _ls_hi in (
            ("commits_since_last_observation", 99),
            ("would_block", 1),
        ):
            event[_ls_key] = _ledger_int_field(event.get(_ls_key), _ls_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_checkpoint_skipped dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-179 W4 (ADR-195) — ledger write-gate discard. Deny-by-default and
    # deliberately STRICTER than the `prompt_injection_detected` branch this
    # producer used to borrow: that branch allowlists `family` by NAME but
    # leaves its VALUE caller-chosen, while this one re-coerces the value
    # against the mirrored catalogue. `decision` and `reason` fall back to
    # the FAIL-CLOSED sentinels ("reject" / "malformed_input") rather than a
    # neutral "other", because an unreadable security verdict is a rejection,
    # never an acceptance. The rejected entry BODY has no allowed field name
    # at all — not even a truncated preview (public repo, LLM06).
    elif action == "ledger_entry_rejected":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEDGER_ENTRY_REJECTED_ALLOWLIST
        )
        if event.get("signal") != _LEDGER_GATE_SIGNAL:
            event["signal"] = _LEDGER_GATE_SIGNAL
        # A ACAO ja e o veredito: `ledger_entry_rejected` so existe para uma
        # entrada REJEITADA. Coagir apenas valores fora do enum deixava passar
        # `decision="accept"` intacto (accept esta NO enum), produzindo um
        # evento ASSINADO cuja acao diz "rejeitada" e cujo campo diz
        # "aceita" — e envenenando a serie de rejeicao/FPR que este ramo
        # deny-by-default existe para proteger. O unico produtor legitimo
        # (`_emit_rejection`) so chega aqui com veredito de rejeicao, entao
        # forcar e coerente com ele e fecha a porta do `emit_generic` direto.
        # (pair-rail do main, rodada 3, P2.)
        # Campos de IDENTIDADE tambem sao entrada: a allowlist os ADMITE, mas
        # nada os validava, entao um chamador direto podia gravar
        # `project="/Users/alice/private"` ou um `session_id` com path no
        # evento ASSINADO — contra o contrato do SPEC/v1, que nega qualquer
        # path nesta acao (pair-rail rodada 6, P2).
        _lg_sid = event.get("session_id")
        if not isinstance(_lg_sid, str) or not _LEDGER_ID_RE.match(_lg_sid):
            event["session_id"] = ""
        _lg_proj = event.get("project")
        if not isinstance(_lg_proj, str) or not _LEDGER_ID_RE.match(_lg_proj):
            event["project"] = ""
        if event.get("decision") != "reject":
            event["decision"] = "reject"
        _lg_reason = event.get("reason")
        if (not isinstance(_lg_reason, str)
                or _lg_reason not in _LEDGER_GATE_REASONS
                # "ok" significa NAO-rejeitada: incoerente com esta acao.
                or _lg_reason == "ok"):
            event["reason"] = "malformed_input"
        _lg_family = event.get("family")
        if (not isinstance(_lg_family, str)
                or _lg_family not in _LEDGER_GATE_FAMILIES):
            event["family"] = "unknown_family"
        for _lg_key, _lg_hi in (
            ("hits_count", 9999),
            # MAX_ENTRY_BYTES of the gate is 8192 and an oversize body is
            # rejected WITHOUT scanning (bytes_scanned=0), so this ceiling
            # can never truncate a legitimate value.
            ("bytes_scanned", 8192),
            ("scanned", 1),
            ("enforced", 1),
        ):
            event[_lg_key] = _ledger_int_field(event.get(_lg_key), _lg_hi)
        if dropped:
            _breadcrumb(
                f"emit_generic ledger_entry_rejected dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-179 W2 US8 (wave-179-close) — SessionEnd memory-delta
    # observation. Dedicated deny-by-default branch (NEVER
    # _EMIT_GENERIC_PASSTHROUGH). The field-name scrub DROPS
    # non-allowlisted keys, so a smuggled memory BASENAME / dir path /
    # $HOME slug never reaches the wire; the closed-enum + TYPE-strict
    # coercions then close the direct emit_generic-caller path (S172
    # doctrine — rejected values are replaced with the safe sentinel,
    # never echoed). Every membership test is isinstance-guarded FIRST:
    # `x in frozenset` raises TypeError when x is UNHASHABLE (a list/dict
    # from a direct caller) and that exception would escape emit_generic's
    # never-raises contract before _write_event's fail-open wrapper could
    # absorb it (PLAN-179 rail finding B / H4 class).
    elif action == "session_memory_delta_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _SESSION_MEMORY_DELTA_OBSERVED_ALLOWLIST
        )
        _smd_outcome = event.get("outcome")
        if (not isinstance(_smd_outcome, str)
                or _smd_outcome not in _SESSION_MEMORY_DELTA_OUTCOMES):
            # NEVER coerced to "written": an unparseable observation must
            # not be laundered into a healthy-class value.
            event["outcome"] = "other"
        _smd_anchor = event.get("anchor_source")
        if (not isinstance(_smd_anchor, str)
                or _smd_anchor not in _SESSION_MEMORY_DELTA_ANCHOR_SOURCES):
            event["anchor_source"] = "none"
        for _smd_key in ("files_count", "modified_count"):
            _smd_val = event.get(_smd_key)
            # TYPE-strict: bool is an int subclass, and a float in an
            # HMAC-covered field drops the WHOLE event at the
            # canonical-json layer — both become the safe sentinel 0,
            # never rounded, never echoed.
            if isinstance(_smd_val, bool) or not isinstance(_smd_val, int):
                event[_smd_key] = 0
            else:
                event[_smd_key] = max(0, min(99999, _smd_val))
        if not isinstance(event.get("index_modified"), bool):
            event["index_modified"] = False
        _smd_sid = event.get("session_id")
        if not isinstance(_smd_sid, str):
            event["session_id"] = ""
        else:
            event["session_id"] = _smd_sid[:128]
        _smd_proj = event.get("project")
        if not isinstance(_smd_proj, str):
            event["project"] = ""
        else:
            event["project"] = _smd_proj[:256]
        if dropped:
            _breadcrumb(
                f"emit_generic session_memory_delta_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H5 (ADR-154) — corrective bash-input rewrite breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The
    # field-name scrub DROPS non-allowlisted keys (so a smuggled command
    # string / remote URL / inline token never reaches the wire); the
    # closed-enum re-coercion + 64-hex hash validation close the direct
    # emit_generic-caller path (S172 doctrine — rejected values are replaced
    # with the safe sentinel, never echoed).
    elif action == "bash_input_rewritten":
        event, dropped = _scrub_ceo_boot_event(
            event, _BASH_INPUT_REWRITTEN_ALLOWLIST
        )
        if event.get("rewrite_class") not in _BASH_REWRITE_CLASSES:
            event["rewrite_class"] = "other"
        if not _is_sha256_hex(event.get("before_sha256")):
            event["before_sha256"] = ""
        if not _is_sha256_hex(event.get("after_sha256")):
            event["after_sha256"] = ""
        if dropped:
            _breadcrumb(
                f"emit_generic bash_input_rewritten dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135 W2 H3 — per-agent SubagentStop lifecycle bracket breadcrumb.
    # Dedicated scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The field-name
    # scrub DROPS non-allowlisted keys (so a smuggled transcript path/body, raw
    # token count, raw wall-time, raw agent_id or marker snippet never reaches
    # the wire); the closed-enum re-coercions close the direct emit_generic-caller
    # path (S172 doctrine — rejected values are replaced with the safe sentinel,
    # never echoed). Every wire field is a closed enum or coarse bucket.
    elif action == "subagent_lifecycle_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST
        )
        if event.get("agent_archetype") not in _SUBAGENT_LIFECYCLE_ARCHETYPES:
            event["agent_archetype"] = "other"
        if event.get("wall_source") not in _SUBAGENT_LIFECYCLE_WALL_SOURCES:
            event["wall_source"] = "unknown"
        if event.get("wall_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["wall_bucket"] = "unknown"
        if event.get("token_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["token_bucket"] = "unknown"
        if event.get("claim_bucket") not in _SUBAGENT_LIFECYCLE_BUCKETS:
            event["claim_bucket"] = "unknown"
        if dropped:
            _breadcrumb(
                f"emit_generic subagent_lifecycle_observed dropped "
                f"forbidden field(s): {sorted(dropped)[:10]}"
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — admin_key_lifecycle_event dedicated
    # deny-by-default scrub branch. Field-name scrub DROPS any non-allowlisted key
    # (a smuggled secret=... can never reach the HMAC-signed wire) AND the VALUE
    # re-coercion closes the direct-emit_generic-caller path: operation + reason
    # reset to their closed enums (else "other"), key_id str-bounded, key_count
    # int-clamped (no float in HMAC-covered fields — S181), rotation_log_appended
    # coerced to a real bool (the SPEC-declared type). NEVER
    # _EMIT_GENERIC_PASSTHROUGH (Sec MF-SEC-2).
    elif action == "admin_key_lifecycle_event":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST
        )
        if "operation" in event and event.get("operation") not in _ADMIN_KEY_OPERATIONS:
            event["operation"] = "other"
        if "reason" in event and event.get("reason") not in _ADMIN_KEY_REASONS:
            event["reason"] = "other"
        if "key_id" in event:
            event["key_id"] = str(event.get("key_id", ""))[:128]
        if "key_count" in event:
            try:
                event["key_count"] = max(0, min(int(event.get("key_count", 0)), 1_000_000))
            except (TypeError, ValueError, OverflowError):
                event["key_count"] = 0
        if "rotation_log_appended" in event:
            # SPEC declares this a BOOL (not 0/1) — coerce to a real bool so a
            # direct caller cannot smuggle a string/int through (Codex R5-R1 P1).
            event["rotation_log_appended"] = str(
                event.get("rotation_log_appended")
            ).strip().lower() in ("1", "true", "yes")
        if dropped:
            _breadcrumb(
                "emit_generic admin_key_lifecycle_event dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — statusline_sidecar_write scrub branch.
    # All fields are numeric / id / digest; sidecar_path length-capped to bound
    # log-line bloat; pct fields are integer BASIS-POINTS clamped to int
    # (PLAN-135-FOLLOWUP-2, S234 — never float; a direct caller cannot smuggle a
    # string OR a float into the signed chain). NEVER _EMIT_GENERIC_PASSTHROUGH.
    elif action == "statusline_sidecar_write":
        event, dropped = _scrub_ceo_boot_event(
            event, _STATUSLINE_SIDECAR_WRITE_ALLOWLIST
        )
        if "sidecar_path" in event:
            event["sidecar_path"] = str(event.get("sidecar_path", ""))[:_STATUSLINE_SIDECAR_PATH_CAP]
        if "plan_id" in event and event.get("plan_id") is not None:
            event["plan_id"] = str(event.get("plan_id"))[:_STATUSLINE_STR_CAP]
        if "digest" in event:
            event["digest"] = str(event.get("digest", ""))[:_STATUSLINE_STR_CAP]
        if "bucket_count" in event:
            try:
                event["bucket_count"] = max(0, min(int(event.get("bucket_count", 0)), 1_000_000))
            except (TypeError, ValueError, OverflowError):
                event["bucket_count"] = 0
        # PLAN-135-FOLLOWUP-2 (S234): integer basis-points, NEVER float — the
        # HMAC canonical encoder rejects float (S181). The producer
        # (.claude/scripts/statusline-ceo.py) owns the pct*100 scaling and emits
        # a finished *_bps int; this scrub is the authoritative Sec MF-3 int
        # coercion boundary — it int-coerces + clamps but NEVER re-scales (a
        # direct caller is contracted to pass basis-points; SPEC v2.46). Ranges
        # DIFFER: context_pct is 0..100% -> 0..10000 bps; buckets_used_pct_max
        # derives from rate-limit used_pct capped at 999% -> 0..99900 bps (NO
        # 100% ceiling, so an over-quota burst is not silently floored).
        # OverflowError (float("inf")) is caught alongside Type/ValueError.
        if (
            "context_pct_bps" in event
            and event.get("context_pct_bps") is not None
        ):
            try:
                event["context_pct_bps"] = max(
                    0, min(10000, int(round(float(event.get("context_pct_bps")))))
                )
            except (TypeError, ValueError, OverflowError):
                event["context_pct_bps"] = None
        if (
            "buckets_used_pct_max_bps" in event
            and event.get("buckets_used_pct_max_bps") is not None
        ):
            try:
                event["buckets_used_pct_max_bps"] = max(
                    0,
                    min(99900, int(round(float(event.get("buckets_used_pct_max_bps"))))),
                )
            except (TypeError, ValueError, OverflowError):
                event["buckets_used_pct_max_bps"] = None
        if dropped:
            _breadcrumb(
                "emit_generic statusline_sidecar_write dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # PLAN-135-FOLLOWUP (Codex R5 P1-2) — model_refusal_observed scrub branch.
    # stop_reason coerced to the const "refusal"; stop_category bounded to the
    # closed provider vocabulary (<=64, non-str → ""); http_status/duration_ms
    # bounded non-negative ints (no float in HMAC-covered fields — S181).
    # NEVER _EMIT_GENERIC_PASSTHROUGH.
    elif action == "model_refusal_observed":
        event, dropped = _scrub_ceo_boot_event(
            event, _MODEL_REFUSAL_OBSERVED_ALLOWLIST
        )
        if "stop_reason" in event:
            event["stop_reason"] = "refusal"
        if "stop_category" in event:
            _cat = event.get("stop_category")
            event["stop_category"] = _cat[:64] if isinstance(_cat, str) else ""
        if "provider" in event:
            event["provider"] = str(event.get("provider", ""))[:64]
        if "model" in event:
            event["model"] = str(event.get("model", ""))[:128]
        for _intf in ("http_status", "duration_ms"):
            if _intf in event:
                try:
                    event[_intf] = max(0, min(int(event.get(_intf, 0)), 1_000_000_000))
                except (TypeError, ValueError, OverflowError):
                    event[_intf] = 0
        if dropped:
            _breadcrumb(
                "emit_generic model_refusal_observed dropped forbidden field(s): %s"
                % sorted(dropped)[:10]
            )
    # ------------------------------------------------------------------
    # PLAN-154 (Gated Learning Loop / ADR-160) — Sec MF-3 scrub branches.
    # Deny-by-default allowlists + VALUE re-coercion by closed-set
    # membership / bounded charset (A2 metadata-only: a direct
    # emit_generic caller can never sign free text into the chain).
    # ------------------------------------------------------------------
    elif action == "lesson_candidate_written":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_CANDIDATE_WRITTEN_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["trigger"] = _learning_token_field(event.get("trigger"))
        if event.get("status") not in _LESSON_CANDIDATE_STATUS_ENUM:
            event["status"] = "QUARANTINED"  # safe floor: never invents PENDING
        if event.get("scan_outcome") not in _LESSON_SCAN_OUTCOME_ENUM:
            event["scan_outcome"] = "scanner_unavailable"
        event["content_sha256"] = _learning_sha256_field(
            event.get("content_sha256"))
        event["scope_tags"] = _learning_scope_tags_field(
            event.get("scope_tags"))
        if dropped:
            _breadcrumb("emit_generic lesson_candidate_written dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_approved":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_APPROVED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["trigger"] = _learning_token_field(event.get("trigger"))
        event["content_sha256"] = _learning_sha256_field(
            event.get("content_sha256"))
        event["scope_tags"] = _learning_scope_tags_field(
            event.get("scope_tags"))
        if dropped:
            _breadcrumb("emit_generic lesson_approved dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_quarantined":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_QUARANTINED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if event.get("reason") not in _LESSON_QUARANTINE_REASON_ENUM:
            event["reason"] = "injection_pattern"
        if event.get("prior_status") != "PENDING":
            event["prior_status"] = "PENDING"  # only legal prior state
        if dropped:
            _breadcrumb("emit_generic lesson_quarantined dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_expired":
        event, dropped = _scrub_ceo_boot_event(event, _LESSON_EXPIRED_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        event["age_days"] = _learning_int_field(event.get("age_days"), 100_000)
        if event.get("created_at_source") not in _LESSON_CREATED_AT_SOURCE_ENUM:
            event["created_at_source"] = "file"
        if dropped:
            _breadcrumb("emit_generic lesson_expired dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_integrity_flag":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_INTEGRITY_FLAG_ALLOWLIST)
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if event.get("check") not in _LESSON_INTEGRITY_CHECK_ENUM:
            event["check"] = "hash_unverifiable"
        if event.get("consumer") not in _LESSON_INTEGRITY_CONSUMER_ENUM:
            event["consumer"] = "boot"
        if dropped:
            _breadcrumb("emit_generic lesson_integrity_flag dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_boot_render_dropped":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_BOOT_RENDER_DROPPED_ALLOWLIST)
        if event.get("reason") not in _LESSON_BOOT_DROP_REASON_ENUM:
            event["reason"] = "other"
        event["lesson_id"] = _learning_token_field(event.get("lesson_id"))
        if dropped:
            _breadcrumb("emit_generic lesson_boot_render_dropped dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "learning_rail_disabled":
        event, dropped = _scrub_ceo_boot_event(
            event, _LEARNING_RAIL_DISABLED_ALLOWLIST)
        if event.get("rail") not in _LEARNING_RAIL_ENUM:
            event["rail"] = "observe"
        if event.get("switch") not in _LEARNING_SWITCH_ENUM:
            event["switch"] = "other"
        if "hook" in event:
            event["hook"] = _learning_token_field(event.get("hook"))
        if dropped:
            _breadcrumb("emit_generic learning_rail_disabled dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "fact_gate_activation_changed":
        event, dropped = _scrub_ceo_boot_event(
            event, _FACT_GATE_ACTIVATION_CHANGED_ALLOWLIST)
        event["enabled"] = bool(event.get("enabled"))
        if event.get("source") not in _FACT_GATE_SOURCE_ENUM:
            event["source"] = "default_advisory"
        if "hook" in event:
            event["hook"] = _learning_token_field(event.get("hook"))
        if dropped:
            _breadcrumb("emit_generic fact_gate_activation_changed dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "advisory_dampened":
        event, dropped = _scrub_ceo_boot_event(
            event, _ADVISORY_DAMPENED_ALLOWLIST)
        event["advisory_id"] = _learning_token_field(event.get("advisory_id"))
        event["ordinal"] = _learning_int_field(event.get("ordinal"), 1_000_000)
        if event.get("channel") not in _ADVISORY_DAMPEN_CHANNEL_ENUM:
            event["channel"] = "stderr_prose"
        if dropped:
            _breadcrumb("emit_generic advisory_dampened dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "distiller_run_completed":
        event, dropped = _scrub_ceo_boot_event(
            event, _DISTILLER_RUN_COMPLETED_ALLOWLIST)
        if event.get("outcome") not in _DISTILLER_OUTCOME_ENUM:
            event["outcome"] = "model_error"  # safe floor: never invents "ok"
        event["model_id"] = _learning_token_field(event.get("model_id"))
        event["fixture_mode"] = bool(event.get("fixture_mode"))
        event["cursor_advanced"] = bool(event.get("cursor_advanced"))
        for _cnt in ("events_consumed", "observations_rejected",
                     "candidates_proposed", "candidates_written",
                     "candidates_quarantined", "rejected_pre_candidate",
                     "tokens_in", "tokens_out"):
            event[_cnt] = _learning_int_field(event.get(_cnt))
        if dropped:
            _breadcrumb("emit_generic distiller_run_completed dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "lesson_evolve_run":
        event, dropped = _scrub_ceo_boot_event(
            event, _LESSON_EVOLVE_RUN_ALLOWLIST)
        event["dry_run"] = bool(event.get("dry_run"))
        for _cnt in ("lessons_scanned", "clusters_found", "clusters_resolved",
                     "proposals_written", "proposals_failed"):
            event[_cnt] = _learning_int_field(event.get(_cnt))
        if dropped:
            _breadcrumb("emit_generic lesson_evolve_run dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "codex_tool_recorded":  # PLAN-155 Wave 4 — Sec MF-3 + coercion
        if event.get("harness") not in _CODEX_HARNESS_ENUM:
            event["harness"] = "codex"
        if event.get("tool_name_enum") not in _CODEX_TOOL_RECORDED_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("hook_event_name") not in _CODEX_TOOL_RECORDED_EVENT_ENUM:
            event["hook_event_name"] = "PostToolUse"
        event, dropped = _scrub_ceo_boot_event(
            event, _CODEX_TOOL_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic codex_tool_recorded dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "codex_turn_ended":  # PLAN-155 Wave 4 — Sec MF-3 + coercion
        if event.get("harness") not in _CODEX_HARNESS_ENUM:
            event["harness"] = "codex"
        if event.get("source") not in _CODEX_TURN_ENDED_SOURCE_ENUM:
            event["source"] = "other"
        event["stop_hook_active"] = bool(event.get("stop_hook_active"))
        event, dropped = _scrub_ceo_boot_event(
            event, _CODEX_TURN_ENDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic codex_turn_ended dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "grok_tool_recorded":  # PLAN-156 Wave 4 — Sec MF-3 + coercion
        if event.get("harness") not in _GROK_HARNESS_ENUM:
            event["harness"] = "grok"
        if event.get("tool_name_enum") not in _GROK_TOOL_RECORDED_TOOL_NAME_ENUM:
            event["tool_name_enum"] = "other"
        if event.get("hook_event_name") not in _GROK_TOOL_RECORDED_EVENT_ENUM:
            event["hook_event_name"] = "PostToolUse"
        event, dropped = _scrub_ceo_boot_event(
            event, _GROK_TOOL_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic grok_tool_recorded dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "grok_turn_ended":  # PLAN-156 Wave 4 — Sec MF-3 + coercion
        if event.get("harness") not in _GROK_HARNESS_ENUM:
            event["harness"] = "grok"
        if event.get("source") not in _GROK_TURN_ENDED_SOURCE_ENUM:
            event["source"] = "other"
        event, dropped = _scrub_ceo_boot_event(
            event, _GROK_TURN_ENDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic grok_turn_ended dropped: %s"
                        % sorted(dropped)[:10])
    elif action == "council_lane_invoked":  # PLAN-156 Wave 6 — Sec MF-3 + coercion
        if event.get("vendor") not in _COUNCIL_VENDOR_ENUM:
            event["vendor"] = "other"
        if event.get("lane_status") not in _COUNCIL_LANE_STATUS_ENUM:
            event["lane_status"] = "other"
        event, dropped = _scrub_ceo_boot_event(
            event, _COUNCIL_LANE_INVOKED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic council_lane_invoked dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-161 W2 C5 — Stop-hook cross-review outcome. Dedicated scrub branch
    # (NEVER _EMIT_GENERIC_PASSTHROUGH). VALUE re-coercion closes the direct
    # emit_generic caller path: an off-enum `outcome` (e.g. raw Codex verdict
    # text) is reset to "skipped_failopen" (never a healthy-class value) and
    # an off-shape `diff_sha256` is reset to "" — so a smuggled finding body
    # / diff excerpt can never reach the signed chain.
    elif action == "codex_review_verdict":
        if event.get("outcome") not in _CODEX_REVIEW_VERDICT_OUTCOME_ENUM:
            event["outcome"] = "skipped_failopen"
        _crv_sha = event.get("diff_sha256")
        if not (isinstance(_crv_sha, str)
                and _CODEX_REVIEW_DIFF_SHA256_RE.fullmatch(_crv_sha)):
            event["diff_sha256"] = ""
        event, dropped = _scrub_ceo_boot_event(
            event, _CODEX_REVIEW_VERDICT_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic codex_review_verdict dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-161 W2 C5 — canonical-edit review-ENTERED denominator. Dedicated
    # scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The ONLY caller fields
    # are session_id + closed-enum tool_name (off-enum -> "unknown") + the
    # bounded 16-hex `file_path_hash_prefix` (r4 F2 legacy bucket key;
    # off-shape -> "") + the exact-16-hex-or-"" `review_id` (r5 F2
    # invocation correlation key; r6 F2: off-shape incl. oversize ->
    # "", dropped never truncated); a raw file path / content body /
    # free text can never reach the wire.
    elif action == "pair_rail_review_expected":
        if event.get("tool_name") not in _PAIR_RAIL_REVIEW_EXPECTED_TOOL_ENUM:
            event["tool_name"] = "unknown"
        _pre_prefix = event.get("file_path_hash_prefix")
        if not (isinstance(_pre_prefix, str)
                and _PAIR_RAIL_FILE_HASH_PREFIX_RE.fullmatch(_pre_prefix)):
            event["file_path_hash_prefix"] = ""
        _pre_rid = event.get("review_id")
        if not (isinstance(_pre_rid, str)
                and _PAIR_RAIL_REVIEW_ID_RE.fullmatch(_pre_rid)):
            event["review_id"] = ""
        # ADR-110-AMEND-2 §1.6 — see the pair_rail_case branch: bounded
        # INTEGER milliseconds; float seconds from a direct caller would
        # drop the whole denominator row at canonical_json.
        if "timeout_ms" in event:
            event["timeout_ms"] = _coerce_pair_rail_timeout_ms(
                event["timeout_ms"]
            )
        event, dropped = _scrub_ceo_boot_event(
            event, _PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic pair_rail_review_expected dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-163 T3.1 — DirectoryAdded workspace-root append. Dedicated scrub
    # branch (NEVER _EMIT_GENERIC_PASSTHROUGH). VALUE re-coercion closes the
    # direct emit_generic caller path: an off-enum `source` is reset to
    # "other" (never echoed) and an off-shape `directory_hash_prefix` is
    # reset to "" — so a raw directory path can never reach the signed chain.
    elif action == "directory_added_recorded":
        # H4 (PLAN-163 fix-pass): membership over an ARBITRARY caller value —
        # an unhashable `source` (dict/list) would raise TypeError on
        # `x in frozenset`, breaking emit_generic's never-raises contract
        # (fail-OPEN by exception). isinstance-guard first: a non-str value
        # is off-enum → reset to the closed default "other" (never echoed).
        _dar_src = event.get("source")
        if not isinstance(_dar_src, str) or _dar_src not in _DIRECTORY_ADDED_SOURCE_ENUM:
            event["source"] = "other"
        _dar_prefix = event.get("directory_hash_prefix")
        if not (isinstance(_dar_prefix, str)
                and _DIRECTORY_ADDED_HASH_PREFIX_RE.fullmatch(_dar_prefix)):
            event["directory_hash_prefix"] = ""
        event, dropped = _scrub_ceo_boot_event(
            event, _DIRECTORY_ADDED_RECORDED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic directory_added_recorded dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-163 T3.2 — Notification lifecycle telemetry. Dedicated scrub
    # branch (NEVER _EMIT_GENERIC_PASSTHROUGH). The harness notification_type
    # enum is OPEN, so an off-enum value (which could be free text) is reset
    # to "other"; `has_title` is coerced to a strict bool; an off-shape
    # `message_sha256_prefix` is reset to "" — message/title TEXT can never
    # reach the signed chain (no-value-echo).
    elif action == "notification_lifecycle":
        # H4 (PLAN-163 fix-pass): same unhashable-value TypeError class as the
        # directory_added_recorded branch above — a dict/list
        # `notification_type` would crash `x in frozenset`. isinstance-guard
        # first so a non-str value is off-enum → reset to "other" (never
        # echoed). has_title below is already bool()-coerced.
        _nl_type = event.get("notification_type")
        if not isinstance(_nl_type, str) or _nl_type not in _NOTIFICATION_TYPE_ENUM:
            event["notification_type"] = "other"
        event["has_title"] = bool(event.get("has_title"))
        _nl_prefix = event.get("message_sha256_prefix")
        if not (isinstance(_nl_prefix, str)
                and _NOTIFICATION_MSG_SHA256_PREFIX_RE.fullmatch(_nl_prefix)):
            event["message_sha256_prefix"] = ""
        event, dropped = _scrub_ceo_boot_event(
            event, _NOTIFICATION_LIFECYCLE_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic notification_lifecycle dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-165 P2 — night-mode posture-toggle forensic record. Dedicated
    # scrub branch (NEVER _EMIT_GENERIC_PASSTHROUGH). VALUE re-coercion
    # closes the direct emit_generic caller path: off-enum mode /
    # previous_mode / result reset to the closed defaults (never echoed) and
    # an off-shape hostname_hash resets to "" — no path, no settings
    # content, no raw hostname can ever reach the signed chain.
    elif action == "night_mode_toggled":
        # isinstance-guard FIRST (H4 class, PLAN-163 fix-pass precedent):
        # membership over an ARBITRARY caller value — an unhashable dict/list
        # would raise TypeError on `x in frozenset`, breaking emit_generic's
        # never-raises contract (fail-OPEN by exception).
        _nm_mode = event.get("mode")
        if not isinstance(_nm_mode, str) or _nm_mode not in _NIGHT_MODE_MODE_ENUM:
            event["mode"] = "other"
        _nm_prev = event.get("previous_mode")
        if not isinstance(_nm_prev, str) or _nm_prev not in _NIGHT_MODE_MODE_ENUM:
            event["previous_mode"] = "other"
        _nm_result = event.get("result")
        if (not isinstance(_nm_result, str)
                or _nm_result not in _NIGHT_MODE_RESULT_ENUM):
            event["result"] = "other"
        _nm_hh = event.get("hostname_hash")
        if not (isinstance(_nm_hh, str)
                and _NIGHT_MODE_HOSTNAME_HASH_RE.fullmatch(_nm_hh)):
            event["hostname_hash"] = ""
        event, dropped = _scrub_ceo_boot_event(
            event, _NIGHT_MODE_TOGGLED_ALLOWLIST)
        if dropped:
            _breadcrumb("emit_generic night_mode_toggled dropped: %s"
                        % sorted(dropped)[:10])
    # PLAN-113 Phase B B-STRUCTURAL — verbatim passthrough for the documented
    # set of TRUSTED first-party producers (see _EMIT_GENERIC_PASSTHROUGH).
    # Their field sets are controlled at the producer site; pass through as-is
    # to preserve the pre-existing accepted contract (no regression).
    elif action in _EMIT_GENERIC_PASSTHROUGH:
        pass
    # PLAN-113 Phase B B-STRUCTURAL — DEFAULT-DENY safety net. Any
    # _KNOWN_ACTIONS member that reached emit_generic WITHOUT an explicit
    # scrub branch, that is NOT a RESERVED action, and that is NOT in the
    # documented verbatim-passthrough set, has ALL caller kwargs dropped: we
    # rebuild the event as just {"action": action} and let _write_event add
    # the framework envelope. This is the safety net for future / unregistered
    # / unexpected producers — closing the ghost-action leak class: a freshly
    # registered action defaults to fail-closed until its author gives it a
    # scrub branch or consciously lists it as a passthrough.
    else:
        event = {"action": action}
        _breadcrumb(
            f"emit_generic {action}: default-deny dropped caller kwargs"
        )
    _write_event(event)
_PLAN088_RATE_LOCK = threading.Lock()
_PLAN090_BUCKET_LOCK = threading.Lock()

# Keep emit_generic and emit_credential_rotation_due here: source/AST consumers
# inspect their literal bodies. Extracted functions share this facade namespace
# so producers, monkeypatches, reloads, and mutable state retain one owner.
from _lib._audit_emit_parts import install as _install_parts

_install_parts(globals(), (
    'actions',
    'boot_schemas',
    'optimizer',
    'federation_schemas',
    'governance',
    'workflow',
    'resource_events',
    'adapters',
    'security',
    'planning',
    'replay',
    'lifecycle_schemas',
    'harness_schemas',
    'compaction',
    'context_pressure',
    'tokens_boot',
    'harness',
    'lifecycle',
    'defense',
    'routing',
    'pair_rail',
    'rate_limits',
    'operations',
    'orchestration',
    'streaming',
    'federation_persona',
    'confidence',
    'finalization',
))


# PLAN-094 Wave A.3 — module-load wire-up for spool-writer integration.
# Executes at first import of audit_emit. Idempotent (set_forensic_emitter
# overwrites callback safely; install_exit_handlers is guarded internally).
# Codex iter-1 P1 fix: spool_writer._forensic calls cb(action, fields)
# (positional dict), but emit_generic signature is (action, **kwargs).
# Adapt via lambda so forensic events don't TypeError.
if _SPOOL_WRITER_AVAILABLE and _spool_writer is not None:
    try:
        _spool_writer.set_forensic_emitter(
            lambda _action, _fields: emit_generic(_action, **_fields)
        )
    except Exception:  # pragma: no cover
        pass
    try:
        _spool_writer.install_exit_handlers()
    except Exception:  # pragma: no cover
        pass
