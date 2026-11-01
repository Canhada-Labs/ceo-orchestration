"""Context pressure.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations
from .compaction import _CONTEXT_PRESSURE_MARKER_GC_MAX
from .compaction import _CONTEXT_PRESSURE_MARKER_TTL_S

__all__ = ('_context_pressure_marker_name', '_context_pressure_bucket_ok', '_GC_SHARDS', '_GC_SHARD_COUNTER_NAME', '_gc_shard_of_name', '_gc_next_shard', '_gc_context_pressure_markers', 'should_emit_context_pressure', 'clear_context_pressure_marker', '_BASH_INPUT_REWRITTEN_ALLOWLIST', '_BASH_REWRITE_CLASSES')

def _context_pressure_marker_name(session_id: Any) -> str:
    """Marker basename for ``session_id`` (PLAN-179 rail finding A).

    Returns the bare project-wide basename when ``session_id`` is absent /
    blank / not a string — the documented degraded mode, in which two
    concurrent sessions in one repo can interfere with each other's
    hysteresis. Otherwise returns ``<basename>.<sanitized-id>``.

    Never raises: this runs inside a fail-open bookkeeping helper.
    """
    if not isinstance(session_id, str):
        return _CONTEXT_PRESSURE_STATE_BASENAME
    raw = session_id.strip()
    if not raw:
        return _CONTEXT_PRESSURE_STATE_BASENAME
    if (len(raw) <= _CONTEXT_PRESSURE_SID_MAX_LEN
            and all(ch in _CONTEXT_PRESSURE_SID_SAFE_CHARS for ch in raw)):
        suffix = raw
    else:
        # Local import: this module keeps hashlib out of its top-level import
        # surface and imports it at the point of use (see _short_hash et al).
        import hashlib
        suffix = hashlib.sha256(
            raw.encode("utf-8", errors="replace")
        ).hexdigest()[:32]
    return _CONTEXT_PRESSURE_STATE_BASENAME + "." + suffix


def _context_pressure_bucket_ok(value: Any) -> bool:
    """Strict INTEGER percent-bucket check for context_pressure_observed.

    Type-strict on purpose. ``40.0 in {40}`` is True in Python (equal
    numbers hash alike), so a plain membership test would wave a FLOAT onto
    the wire — and a float under the HMAC chain DISCARDS THE WHOLE EVENT
    (S181 / ADR-055-AMEND-2), not just the offending field. ``bool`` is
    rejected explicitly because it is an ``int`` subclass and ``True`` would
    otherwise sail through any numeric check.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value in _CONTEXT_PRESSURE_USED_BUCKETS_PCT


# PLAN-179 rail round-5 [P2] — rotating identity shards, best-effort sweep.
# A shard selects eligible names; it does not preserve directory position.
# Each sweep starts a fresh scandir and can hit its deadline before the
# same tail, so expired markers there have no guaranteed reclamation.
_GC_SHARDS = 8


# Contador de VARREDURA (rail round-6 [P2]): o shard avanca por SWEEP, nunca
# pelo relogio — varreduras no mesmo minuto modulo K starvariam as outras.
_GC_SHARD_COUNTER_NAME = ".gc-shard-cursor"


def _gc_shard_of_name(name):
    """Shard estavel derivado do NOME (nunca da ordem de leitura)."""
    try:
        return zlib.crc32(name.encode("utf-8", "replace")) % _GC_SHARDS
    except Exception:
        return 0


def _gc_next_shard(state_dir):
    """Select the next shard from a best-effort persisted counter.

    A successful read/write advances the counter. A failed read seeds it
    from randomness (zero if randomness also fails); a failed write can
    leave the same counter for the next sweep. This selects eligible names,
    without guaranteeing that the deadline-bounded scan reaches each name.
    The counter read and ancestor paths retain the rc.1 condition 28 limits;
    O_NOFOLLOW here protects only the temporary file used for the write.
    """
    counter_path = Path(str(state_dir)) / _GC_SHARD_COUNTER_NAME
    current = None
    try:
        raw = counter_path.read_text(encoding="utf-8").strip()
        current = int(raw)
    except Exception:
        current = None
    if current is None:
        try:
            current = int.from_bytes(os.urandom(2), "big")
        except Exception:
            current = 0
    nxt = (current + 1) % (_GC_SHARDS * 1024)  # espaco folgado, sem overflow
    try:
        counter_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = counter_path.parent / (
            "." + counter_path.name + "." + str(os.getpid()) + "."
            + os.urandom(4).hex() + ".tmp"
        )
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(tmp), flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(str(nxt))
        except Exception:
            try:
                os.unlink(str(tmp))
            except OSError:
                pass
            raise
        os.replace(str(tmp), str(counter_path))
    except Exception:
        pass  # housekeeping: nao persistir custa cobertura, nunca correcao
    return nxt % _GC_SHARDS


def _gc_context_pressure_markers(
    state_dir: Any,
    ttl_seconds: int = _CONTEXT_PRESSURE_MARKER_TTL_S,
    max_files: int = _CONTEXT_PRESSURE_MARKER_GC_MAX,
) -> int:
    """Unlink aged-out per-session markers. Bounded, fail-open (finding A).

    Per-session keying trades one shared file for one file per session, so
    it must come with its own reclaim or it re-opens the unbounded-growth
    class the rail rejected in the session STORES (finding C). Markers are
    ~4 bytes and are only created on a rung TRANSITION with the progress
    floor armed, so the rate is low — this sweep exists so "low" never
    becomes "forever".

    Only names carrying the marker prefix AND a suffix are considered; the
    project-wide marker itself is never collected (it has no suffix), and an
    unrelated file in ``.claude/state/`` is left alone. Returns the number
    of files unlinked; every OSError is swallowed (housekeeping).
    """
    removed = 0
    prefix = _CONTEXT_PRESSURE_STATE_BASENAME + "."
    try:
        cutoff = time.time() - float(ttl_seconds)
        directory = Path(str(state_dir))
        # PLAN-179 rail rounds 2/3/4 [P2] — same story as the twin sweep in
        # `scratchpad_lib.gc_orphan_session_stores`, and the same conclusion.
        # r2 removed the sort+materialise; r3 replaced it with a fixed prefix
        # window that STARVED the tail; r4 showed the rotating offset was still
        # `% _scan_cap`, so nothing past ~2x that was ever reachable.
        # Scan lazily without sorting, stopping at `max_files` deletions
        # or the wall-clock deadline. The deadline can repeatedly leave
        # the same tail unvisited: shard rotation alone does not guarantee
        # coverage. A continuation mechanism remains an rc.1 P2 follow-up.
        _deadline = time.time() + _GC_MARKER_WALL_BUDGET_S
        _shard = _gc_next_shard(directory)
        _scanned = 0
        _it = os.scandir(str(directory))
        try:
            for _de in _it:
                _scanned += 1
                if removed >= int(max_files):
                    break
                if (_scanned & 63) == 0 and time.time() >= _deadline:
                    break
                entry = Path(_de.path)
                name = entry.name
                if _gc_shard_of_name(name) != _shard:
                    continue
                # Both the live marker `<prefix><sid>` and a crash-orphaned
                # atomic-write temp `.<prefix><sid>.<pid>.<rand>.tmp`.
                if name.startswith("."):
                    name = name[1:]
                if not name.startswith(prefix) or len(name) <= len(prefix):
                    continue
                try:
                    if entry.stat().st_mtime >= cutoff:
                        continue
                    entry.unlink()
                    removed += 1
                except OSError:
                    # Per-entry fail-open: a racing unlink must not abort it.
                    continue
        finally:
            try:
                _it.close()
            except Exception:
                pass
    except (OSError, TypeError, ValueError):
        return removed
    return removed


# QDSAA-FUNCAO-LONGA: Preserve the existing marker expiry, sharded GC, and edge-trigger sequence during relocation.
def should_emit_context_pressure(
    used_bucket: Any, state_dir: Any, session_id: Any = None
) -> bool:
    """Return True only on a bucket TRANSITION (PLAN-179 W0 US2 / 8.1).

    ``state_dir`` is the directory holding the marker — callers pass
    ``<project>/.claude/state``. The marker records the last percent bucket
    observed; a repeat of the same bucket returns False, a transition in
    EITHER direction returns True and re-arms the marker. This is
    hysteresis, not sampling: without it the rail emits one row per prompt
    while the session sits in a single rung, which is exactly the flood the
    HMAC chain must not carry.

    ``session_id`` (PLAN-179 rail finding A, round-1 REJECT) KEYS that
    marker. It must be the TRUSTED id — the one the harness put in the hook
    input (``scratchpad_lib.session_id_from_event``), never
    ``CLAUDE_SESSION_ID`` from the environment, which any agent with a
    subshell can set (consensus M2). Passing None is legal and means the
    DEGRADED project-wide marker: hysteresis then behaves as it did before
    this fix, i.e. two concurrent sessions in the same repo suppress and
    re-arm each other and the wire rows cannot be attributed. Callers that
    have a trusted id must pass it; callers that do not should say so on the
    wire by omitting ``session_id`` from the event rather than inventing one.

    FAIL-OPEN on infrastructure (house rule): any state I/O error — absent
    directory, unwritable path, corrupt or truncated marker — means
    "emit", and the caller is never allowed to see an exception. The caller
    is a hook; a bookkeeping file may not block or crash a user session.
    Fail-open costs at most a duplicate breadcrumb, whereas fail-closed
    would silently lose the very signal PLAN-179 exists to measure.
    """
    if not _context_pressure_bucket_ok(used_bucket):
        # Off-enum input must never re-arm the marker (that would let a
        # bogus value suppress the NEXT real transition). The dispatch
        # branch coerces the field itself, so there is nothing to debounce.
        return True
    try:
        marker = Path(str(state_dir)) / _context_pressure_marker_name(session_id)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return True
    current = str(int(used_bucket))
    previous = None  # type: Optional[str]
    try:
        previous = marker.read_text(encoding="utf-8").strip()
    except (OSError, ValueError, UnicodeDecodeError):
        previous = None
    if previous == current:
        return False
    # Re-arm atomically (tmp + os.replace, 0600) — same idiom as
    # check_directory_added._atomic_write, kept inline so audit_emit gains
    # no new import.
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        # PLAN-179 rail finding A: the tmp name is derived from the SAME
        # per-session marker name. Reusing the bare basename here would give
        # two sessions re-arming at the same moment one shared tmp path.
        # PLAN-179 rail round-3 [P1] — SYMLINK-SAFE, and the name is not
        # guessable. `.claude/state/` is gitignored and world-writable to
        # anything running as this user, so a PREDICTABLE tmp path could be
        # pre-created as a symlink; a plain `open(..., "w")` follows it and the
        # hook then truncates whatever it points at — an arbitrary-write
        # primitive that routes around every canonical-edit guard, reached
        # through an advisory audit helper. Three things close it together:
        # O_EXCL (refuses an existing path), O_NOFOLLOW (refuses a symlink even
        # if it appears between the check and the open), and a random suffix so
        # pre-creation is not feasible in the first place. The mode is set AT
        # CREATION, which also removes the window the old separate `chmod` left.
        _rand = os.urandom(6).hex()
        tmp = marker.parent / (
            "." + marker.name + "." + str(os.getpid()) + "." + _rand + ".tmp"
        )
        _flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        _flags |= getattr(os, "O_NOFOLLOW", 0)  # POSIX; 0 is a safe no-op
        _fd = os.open(str(tmp), _flags, 0o600)
        try:
            with os.fdopen(_fd, "w", encoding="utf-8") as fh:
                fh.write(current + "\n")
        except Exception:
            # Never leave the temp behind on a failed write — the GC below
            # only sweeps by AGE, so an orphan would linger for a full TTL.
            try:
                os.unlink(str(tmp))
            except OSError:
                pass
            raise
        os.replace(str(tmp), str(marker))
    except (OSError, ValueError):
        _breadcrumb(
            "should_emit_context_pressure: marker re-arm failed — "
            "fail-open (the same bucket may emit twice)"
        )
    # PLAN-179 rail finding A: reclaim runs ONLY on the re-arm path, i.e. on a
    # rung TRANSITION, which is rare by construction (that is the whole point
    # of the hysteresis above). It is bounded and fail-open by its own
    # contract, and its result cannot change what this function returns.
    _gc_context_pressure_markers(marker.parent)
    return True


def clear_context_pressure_marker(state_dir: Any, session_id: Any = None) -> None:
    """Re-arma a histerese de pressão após uma compactação (rail round-10 [P1]).

    O produtor é PreCompact-only: nada observa a QUEDA de contexto pós-
    compactação, então uma sessão que compacta duas vezes no mesmo degrau
    mantém previous==current e a segunda travessia genuína é suprimida.
    O PostCompact chama isto para fechar a GERAÇÃO de compactação:
    remover o marker re-arma o debounce para o próximo ciclo.

    FAIL-OPEN (regra da casa): qualquer erro de I/O é engolido — um unlink
    de bookkeeping nunca pode quebrar um hook. Marker ausente é o caso
    normal (sessão que nunca cruzou um degrau)."""
    try:
        marker = Path(str(state_dir)) / _context_pressure_marker_name(session_id)
        marker.unlink()
    except (OSError, TypeError, ValueError):
        pass


# PLAN-135 W2 H5 (ADR-154) — Sec field allowlist for the bash-input-rewrite
# breadcrumb (bash_input_rewritten, producer .claude/hooks/check_bash_safety.py).
# Deny-by-default. Same no-value-echo contract as settings_tamper_detected
# ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]): the
# command STRING (before OR after the rewrite), the remote URL / refspec and
# any inline credential are NEVER allowed fields — only the closed-enum
# rewrite_class + the two 64-hex sha256 hashes travel on the wire. The hash
# pair lets an auditor prove audited-cmd == executed-cmd without seeing either.
_BASH_INPUT_REWRITTEN_ALLOWLIST = frozenset({
    "action", "session_id", "project",
    "rewrite_class", "before_sha256", "after_sha256",
    # _write_event envelope (pre-allowed so scrub doesn't strip on round-trip):
    "ts", "event_schema",
    "tokens_in", "tokens_out", "tokens_total",
    "hmac", "hmac_error",
})


# PLAN-135 W2 H5 — closed enum for the rewrite class. The pilot ships EXACTLY
# one rewrite pattern; widening requires a new ADR + Codex (Doctrine 1
# corollary + ADR-154 §1 single-rewriter invariant). Anything outside the set
# (incl. a missing field) is COERCED to "other" (S172 doctrine — the rejected
# value is never echoed).
_BASH_REWRITE_CLASSES = frozenset({
    "git_push_force_to_lease",
    "other",
})
