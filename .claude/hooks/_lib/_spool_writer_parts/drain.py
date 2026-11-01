# PLAN-094 Wave A — spool_writer (canonical promotion of spool_writer_DRAFT.py)
"""_lib/spool_writer.py — durable spool + drain-on-next-invoke (PLAN-094 Wave A).

Implements ADR-055-AMEND-1: 5-phase atomic drain protocol, 4-tuple total
order across concurrent producers, K_MAX/K_TAIL_WINDOW idempotent skip,
canonical-tail prev_hmac reconstruction, per-PID spool + per-PID journal,
atomic split-and-delete for K_MAX deferral, header/body uuid sentinel.

Stdlib-only (ADR-002). Fail-open invariant — never raise to caller; any
infra failure emits a breadcrumb and returns safely.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import secrets
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
from _lib import runtime_paths as _runtime_paths  # noqa: E402  # PLAN-182 W1 single resolver (ADR-001 S318)

try:
    from _lib import audit_hmac as _audit_hmac  # noqa: E402
    _HMAC_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_hmac = None  # type: ignore[assignment]
    _HMAC_AVAILABLE = False

try:
    from _lib import canonical_json as _canonical_json  # noqa: E402
except Exception:  # pragma: no cover
    _canonical_json = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants (ADR-055-AMEND-1 §3 wave A spec)
# ---------------------------------------------------------------------------

K_MAX = 100
K_TAIL_WINDOW = 200
SPOOL_HEADER_VERSION = 1
# PLAN-111 Wave B-alt4 (debate consensus + cProfile data-driven): trigger
# raised 50 -> 100. Halves drain cascade count (40 -> 20 across 5-trial
# emit_pair benchmark, confirmed by cprofile-post-b-darwin.txt). Per-trial
# wall-clock 174ms -> 170ms (-2%); cumulative drain_now cumtime 364ms -> 307ms.
# Combined with Wave A cache: per-emit 580us -> 425us (-27%). AC-C1 strict
# <=360us NOT hit alone; Wave C.1 RELAX path engaged (200->300ms test
# budget) with ubuntu projection ~255ms still well under.
DRAIN_TRIGGER_SIZE = 100
DRAIN_TRIGGER_MTIME_MS = 100
STALE_SPOOL_TTL_DAYS = 7
SPOOL_LOCK_TIMEOUT = 2.5


__all__ = (
    '_phase4_build_batch',
    '_phase5_append_canonical',
    '_phase5_split_and_cleanup',
    '_journal_compact_drained',
)

# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _phase4_build_batch(
    deduped: List[Tuple[Tuple[int, int, str, int], Dict[str, Any], _DrainingFile, int]],
    drain_epoch: str,
    in_recovery: bool,
    stats: DrainStats,
    starting_processed: int = 0,
) -> Tuple[List[bytes], List[_DrainingFile], Dict[str, Set[int]], Optional[bytes], List[Tuple[str, int]]]:
    """Compute HMAC chain; produce canonical-log batch lines.

    Returns (batch_line_bytes, fully_consumed_files,
    per_file_consumed_indices, last_hmac_bytes, drained_record_ids_by_pid).

    iter2-P0-1: per_file_consumed is now Dict[str, Set[int]] (body indices,
    not a prefix-count). Phase 5 splits the remainder using the COMPLEMENT
    of the set — out-of-order index consumption (e.g. clock-skew rollback
    where a LATER body index sorts ahead of an EARLIER one and is cut by
    K_MAX) no longer trashes unprocessed earlier lines.

    iter2-P1-1: idempotent-skip branch now ALSO appends (record_id, pid)
    to drained_ids and marks the index consumed — without this, the matching
    journal `commit` envelope stays as commit_no_drained forever (phantom
    inflight count in AC10).

    iter2-P2-1: canonical output honors the SOURCE file's drain_epoch
    (src_file.drain_epoch) — important for forensic correlation when an
    in-recovery drain re-emits entries from a prior-cycle .draining file.

    iter3-P0-1: K_MAX counts TOTAL PROCESSED entries (appended + idempotent
    skipped + intentionally consumed via tamper/duplicate paths), NOT just
    appended. Without this, repeated partial-crash cycles where each crash
    leaves K_MAX entries in .draining and the next drain hits all K_MAX as
    skipped + processes K_MAX fresh can accumulate >K_TAIL_WINDOW processed
    entries per cycle → entries fall out of the skip-guard tail window on
    a subsequent crash cycle → re-appended duplicates in canonical log.
    Capping TOTAL processed bounds disk-write + idempotent work per drain
    cycle so window-overflow cannot occur.

    Honors K_MAX cap; remaining un-consumed entries are left for the next
    drain cycle via Phase 5 atomic split.
    """
    log_path = _canonical_log_path()

    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.1 — Path B variant 1 hoist.
    # Probe rotation BEFORE reading canonical tail (and therefore before
    # computing prev_hmac), so this batch always anchors against the
    # CURRENT canonical file (post-rotation if applicable).
    #
    # Prior bug: Phase 4 read prev_hmac from the about-to-rotate file;
    # Phase 5 detected rotation but batch_lines were already HMAC-chained
    # against the old chain → verifier (resets at file boundary per
    # ADR-055 §2) saw STATUS_TAMPER at line 1 of the new file.
    # Per F-7.7 (PLAN-112 wave-c-bundles/C10) + D3 confirmation.
    # Fail-open: any rotation exception is breadcrumbed and the read
    # proceeds against whatever log path is current.
    try:
        from _lib import audit_emit as _audit_emit_lazy
        from _lib import audit_hmac as _audit_hmac_lazy
        # PLAN-143 item-2 (audit-errors-02): guard the rotation probe.
        # Under test/shim wiring the lazily-imported object can be an
        # _EmitCapture double that lacks _rotate_if_needed_safe; calling
        # it raised AttributeError into the fail-open except below, which
        # breadcrumbed cosmetic audit-log.errors noise and silently
        # skipped the probe. getattr-guard -> no attribute means "no
        # rotation" (None), taking the same intended branch without noise.
        _rotate_probe = getattr(
            _audit_emit_lazy, "_rotate_if_needed_safe", None
        )
        rotated_to_phase4 = (
            _rotate_probe(log_path) if callable(_rotate_probe) else None
        )
        if rotated_to_phase4 is not None and not _audit_hmac_lazy.is_disabled():
            try:
                _audit_hmac_lazy.reset_chain_on_rotation()
            except Exception as re:
                _breadcrumb(
                    f"phase4 rotation HMAC reset failed: "
                    f"{type(re).__name__}: {re}"
                )
            # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — emit
            # chain_reset_marker as line 1 of new file + manifest. Fail-open
            # (marker absence → verifier legacy mode, not tamper signal).
            try:
                _audit_emit_lazy._emit_chain_reset_marker_under_lock(
                    log=log_path,
                    previous_archive_path=str(rotated_to_phase4),
                    rotation_trigger="size_threshold",
                )
            except Exception as me:
                _breadcrumb(
                    f"phase4 chain_reset_marker emit failed: "
                    f"{type(me).__name__}: {me}"
                )
    except Exception as e:
        # Fail-open: rotation probe never blocks the canonical read.
        _breadcrumb(f"phase4 rotation probe failed: {type(e).__name__}: {e}")

    # AFTER rotation probe: read tail from (now-current) file.
    prev_hmac, tail_entries = _read_canonical_tail(log_path, K_TAIL_WINDOW)
    drain_sha_set: set = set()
    for e in tail_entries:
        ds = e.get("_drain_sha256")
        if isinstance(ds, str) and len(ds) == 64:
            drain_sha_set.add(ds)

    if _HMAC_AVAILABLE and _audit_hmac is not None and prev_hmac is None:
        # Empty log + HMAC available → genesis (which is correct
        # post-rotation since the new file is empty).
        prev_hmac = _audit_hmac.GENESIS_PREV

    batch_lines: List[bytes] = []
    # iter2-P0-1: set-of-indices, not prefix-count.
    per_file_consumed: Dict[str, Set[int]] = {}
    drained_ids: List[Tuple[str, int]] = []  # P1-3: (record_id, pid)
    last_hmac: Optional[bytes] = prev_hmac

    def _mark(path_str: str, idx: int) -> None:
        per_file_consumed.setdefault(path_str, set()).add(idx)

    # iter3-P0-1: cap on TOTAL processed (appended + idempotent_skipped +
    # tamper-consumed); breaking on appended-only allowed cumulative
    # processed > K_TAIL_WINDOW across recovery cycles → window overflow.
    # iter4-P2-2: `starting_processed` carries duplicate-cleanup count from
    # Phase 3 so combined Phase-3 + Phase-4 work ≤ K_MAX per drain cycle.
    processed = starting_processed
    for key, entry, src_file, body_idx in deduped:
        if processed >= K_MAX:
            break
        path_key = str(src_file.path)

        # P1-3: pull record_id off the spool entry BEFORE stripping internal
        # fields so we can emit op:"drained" with the matching id.
        rec_id = entry.get("record_id")

        entry_clean = {
            k: v for k, v in entry.items()
            if not (isinstance(k, str) and k.startswith("_drain_"))
            and k != "hmac" and k != "hmac_error"
        }
        try:
            sha = _sha256_of_canonical_json(entry_clean)
        except Exception as e:
            _breadcrumb(f"sha compute failed: {type(e).__name__}: {e}")
            # Treat unencodable entry like a tamper — skip + count
            stats.partial_lines_discarded += 1
            _mark(path_key, body_idx)
            # iter3-P0-1: tamper-consumed counts toward K_MAX budget
            processed += 1
            continue

        if sha in drain_sha_set:
            stats.skipped_idempotent += 1
            severity = "INFORMATIONAL" if in_recovery else "ALARM"
            _forensic("audit_spool_unexpected_skip", {
                "drain_epoch": drain_epoch,
                "spool_uuid": key[2],
                "ordinal_within_file": key[3],
                "skipped_sha256": sha,
                "drain_in_recovery_mode": in_recovery,
                "severity": severity,
            })
            _mark(path_key, body_idx)
            # iter2-P1-1: also commit drained_id so the journal compactor
            # emits op:"drained" for this record. Without this, the matching
            # `commit` envelope stays as commit_no_drained forever in the
            # journal (AC10 phantom inflight). The canonical batch line was
            # already appended on the prior crashed drain — this entry is
            # "drained" from the journal's perspective even though we are
            # not re-appending the bytes this cycle.
            if isinstance(rec_id, str) and rec_id:
                drained_ids.append((rec_id, src_file.pid))
            # iter3-P0-1: idempotent-skip counts toward K_MAX budget so
            # window-overflow on multi-crash cycles is structurally
            # impossible (processed ≤ K_MAX < K_TAIL_WINDOW).
            processed += 1
            continue

        chained = dict(entry_clean)
        chained["_drain_sha256"] = sha
        # iter2-P2-1: honor source file's drain_epoch for forensic
        # correlation (this entry was first staged in that cycle).
        chained["_drain_epoch"] = src_file.drain_epoch

        if (_HMAC_AVAILABLE and _audit_hmac is not None
                and not _audit_hmac.is_disabled()):
            try:
                key_bytes = _audit_hmac.get_or_create_key()
                digest = _audit_hmac.compute_entry_hmac(
                    key_bytes,
                    last_hmac if last_hmac is not None else _audit_hmac.GENESIS_PREV,
                    chained,
                )
                chained["hmac"] = digest.hex()
                last_hmac = digest
            except _audit_hmac.AuditProducerPathPollutionError as ppe:
                # PLAN-118 AC-B4 chokepoint 4 / recursion-safety case 5 —
                # the spool fast-path (audit_emit._write_event line 1760)
                # appends to spool BEFORE local HMAC computation; the
                # HMAC is then computed HERE at drain time. On
                # canonical-resolution mismatch at drain: refuse to
                # compute HMAC for the batch entry; normalize the entry
                # to hmac:null + closed-enum hmac_error BEFORE the entry
                # is appended to the chain (so polluted HMACs never enter
                # the chain at all). Emit AC-B5 breadcrumb with
                # chokepoint=spool_drain (safe — the typed emitter's own
                # _write_event call will also trigger this same
                # exception and recurse-fail-OPEN through the same
                # channel; the breadcrumb's purpose is exactly that
                # forensic signal).
                chained["hmac"] = None
                chained["hmac_error"] = "producer_path_pollution_detected"
                _breadcrumb(
                    f"hmac_error: producer_path_pollution_detected "
                    f"(chokepoint=spool_drain): {ppe}"
                )
                # Parse the exception payload for the AC-B5 breadcrumb.
                try:
                    _msg = str(ppe)
                    _rc = "audit_emit_path_pollution"
                    _psp = "00000000"
                    _ecp = "00000000"
                    _valid_rcs = (
                        "audit_emit_path_pollution",
                        "canonical_json_path_pollution",
                        "audit_hmac_path_pollution",
                    )
                    for _tok in _msg.split():
                        if _tok.startswith("reason_code="):
                            _cand = _tok.split("=", 1)[1]
                            if _cand in _valid_rcs:
                                _rc = _cand
                        elif _tok.startswith("path_sha256_prefix="):
                            _cand = _tok.split("=", 1)[1]
                            if len(_cand) == 8 and all(c in "0123456789abcdef" for c in _cand):
                                _psp = _cand
                        elif _tok.startswith("expected_canonical_prefix="):
                            _cand = _tok.split("=", 1)[1]
                            if len(_cand) == 8 and all(c in "0123456789abcdef" for c in _cand):
                                _ecp = _cand
                    # Lazy-import the typed emitter to avoid circular import
                    # at module load (spool_writer is imported from audit_emit).
                    from _lib import audit_emit as _audit_emit
                    _audit_emit.emit_audit_producer_path_pollution_detected(
                        chokepoint="spool_drain",
                        reason_code=_rc,
                        path_sha256_prefix=_psp,
                        expected_canonical_prefix=_ecp,
                    )
                except Exception as _be:  # pragma: no cover
                    _breadcrumb(
                        f"AC-B5 spool_drain breadcrumb emit failed: "
                        f"{type(_be).__name__}: {_be}"
                    )
            except Exception as e:
                chained["hmac"] = None
                chained["hmac_error"] = f"{type(e).__name__}: {e}"
                _breadcrumb(f"hmac compute failed: {type(e).__name__}: {e}")

        try:
            line = json.dumps(
                chained, separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as e:
            _breadcrumb(f"phase4 encode failed: {type(e).__name__}: {e}")
            _mark(path_key, body_idx)
            # iter3-P0-1: encode-failure consumed counts toward K_MAX.
            processed += 1
            continue
        batch_lines.append(line)
        _mark(path_key, body_idx)
        # P1-3: track for op:"drained" envelope emission
        if isinstance(rec_id, str) and rec_id:
            drained_ids.append((rec_id, src_file.pid))
        # iter3-P0-1: append counts toward K_MAX (was: `appended += 1`).
        processed += 1

    fully_consumed: List[_DrainingFile] = []
    return batch_lines, fully_consumed, per_file_consumed, last_hmac, drained_ids


# ---------------------------------------------------------------------------
# Phase 5 — atomic append + split + cleanup
# ---------------------------------------------------------------------------


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _phase5_append_canonical(
    batch_lines: List[bytes], last_hmac: Optional[bytes]
) -> int:
    """Append batch to canonical log; single fsync; update sidecar cache.

    iter2-P2-3: chain_length sidecar increment counts HMAC-bearing lines
    only — entries that failed HMAC compute (hmac=null + hmac_error set)
    don't extend the chain even though their bytes are appended. The
    sidecar is a cache for chain-verify performance; counting null-hmac
    lines would diverge from the true HMAC chain length.
    """
    if not batch_lines:
        return 0
    log_path = _canonical_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    # PLAN-094-FOLLOWUP Wave A.3-rotation — probe rotation BEFORE the
    # canonical append so spool-drained writes never accumulate past the
    # configured threshold. Lazy-import audit_emit (circular dep at
    # module load time) + audit_hmac for chain reset.
    try:
        from _lib import audit_emit as _audit_emit_lazy
        from _lib import audit_hmac as _audit_hmac_lazy
        # PLAN-143 item-2 (audit-errors-02): guard the rotation probe — a
        # capture-shim object may lack _rotate_if_needed_safe (see the
        # phase-4 probe above). getattr-guard -> missing attribute means
        # "no rotation" (None), no AttributeError into the fail-open path.
        _rotate_probe = getattr(
            _audit_emit_lazy, "_rotate_if_needed_safe", None
        )
        rotated_to = (
            _rotate_probe(log_path) if callable(_rotate_probe) else None
        )
        if rotated_to is not None and not _audit_hmac_lazy.is_disabled():
            try:
                _audit_hmac_lazy.reset_chain_on_rotation()
                # Reset last_hmac so this batch re-anchors at genesis.
                last_hmac = None
            except Exception as re:
                _breadcrumb(
                    f"phase5 rotation HMAC reset failed: "
                    f"{type(re).__name__}: {re}"
                )
    except Exception as e:
        # Fail-open: rotation probe never blocks the canonical append.
        _breadcrumb(f"phase5 rotation probe failed: {type(e).__name__}: {e}")

    payload = b"".join(batch_lines)
    fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)

    if (_HMAC_AVAILABLE and _audit_hmac is not None
            and not _audit_hmac.is_disabled()
            and last_hmac is not None
            and len(last_hmac) == _audit_hmac.HMAC_BYTES):
        try:
            _audit_hmac.write_last_hmac(last_hmac)
        except Exception as e:
            _breadcrumb(f"write_last_hmac failed: {type(e).__name__}: {e}")
        # iter2-P2-3: count HMAC-bearing lines only.
        hmac_bearing = 0
        for line in batch_lines:
            try:
                obj = json.loads(line.rstrip(b"\n").decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(obj, dict):
                continue
            hx = obj.get("hmac")
            if isinstance(hx, str) and len(hx) == 64:
                hmac_bearing += 1
        try:
            current = _audit_hmac.read_chain_length()
            _audit_hmac.write_chain_length(current + hmac_bearing)
        except Exception as e:
            _breadcrumb(f"chain_length update failed: {type(e).__name__}: {e}")
    return len(batch_lines)


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _phase5_split_and_cleanup(
    files: List[_DrainingFile],
    per_file_consumed: Dict[str, Set[int]],
    drain_epoch: str,
    stats: DrainStats,
) -> None:
    """For each draining file: unlink if fully consumed; else atomic-split.

    iter2-P0-1: per_file_consumed is a Set[int] of body INDICES. The
    remainder file is built from the COMPLEMENT (all body indices NOT in
    the set). This correctly handles out-of-order index consumption (e.g.
    wall_ns clock-skew rollback where a later body index sorts BEFORE an
    earlier one and is cut by K_MAX) — prefix-based cleanup would have
    discarded unprocessed earlier lines.

    iter2-P0-3: SKIP any _DrainingFile whose .quarantined flag is set —
    the file is already renamed to .malformed.<epoch>; trying to split
    or unlink the original path would either fail (ENOENT) or, worse,
    re-sweep the renamed quarantined file on a subsequent drain.

    iter2-P1-3: when splitting, mint a NEW drain_epoch for the destination
    so dst path != src path. This closes the `.split.tmp` two-step window
    (old code reused src epoch → dst==src → os.rename(src,dst) no-op AND
    the temp suffix dance remained). Now: tmp → fsync → rename(tmp,
    new_dst) atomic; unlink(src). Single window if rename succeeds.

    P2-4: header is written VERBATIM from file.header_raw — no JSON
    re-encode (preserves byte identity of _spool_uuid sentinel chain).
    """
    for f in files:
        # iter2-P0-3: skip quarantined files — original path doesn't exist
        # at .draining.<epoch> anymore; it was renamed to .malformed.<epoch>.
        if f.quarantined:
            continue
        path_key = str(f.path)
        if f.header is None and not f.body_lines:
            # Already empty (no body) — just unlink the (header-only) file.
            try:
                if f.path.exists():
                    os.unlink(str(f.path))
            except OSError:
                pass
            continue
        consumed_set = per_file_consumed.get(path_key, set())
        total = len(f.body_lines)
        # iter2-P0-1: fully consumed iff every body index is in the set.
        if total == 0 or all(i in consumed_set for i in range(total)):
            try:
                os.unlink(str(f.path))
                stats.files_consumed_fully += 1
            except OSError as e:
                _breadcrumb(f"phase5 unlink failed: {type(e).__name__}: {e}")
            continue

        # iter2-P1-3: mint a NEW epoch for the split destination so
        # dst_path differs from src_path; this collapses the prior
        # two-step `.split.tmp` rename dance into a single rename+unlink.
        new_epoch = secrets.token_hex(4)
        tmp_token = secrets.token_hex(4)
        # tmp is a sibling .tmp.<token> for atomic create+rename within same dir
        tmp_path = f.path.with_name(f.path.name + _TMP_SUFFIX_TOKEN + tmp_token)
        try:
            # P2-4: verbatim header bytes — no JSON re-encode
            header_line = f.header_raw if f.header_raw else (
                json.dumps(
                    f.header, separators=(",", ":"), ensure_ascii=False,
                ).encode("utf-8") + b"\n"
            )
            # iter2-P0-1: rebuild remainder using COMPLEMENT of consumed_set
            # (NOT a prefix slice). Empty lines are preserved as empty bytes
            # in body_lines and re-emitted with the newline separator below.
            remainder_lines = [
                f.body_lines[i] for i in range(total) if i not in consumed_set
            ]
            body_remainder = b"\n".join(remainder_lines)
            if body_remainder and not body_remainder.endswith(b"\n"):
                body_remainder += b"\n"
            fd = os.open(
                str(tmp_path),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC,
                0o600,
            )
            try:
                os.write(fd, header_line)
                if body_remainder:
                    os.write(fd, body_remainder)
                os.fsync(fd)
            finally:
                os.close(fd)
            # iter2-P1-3: dst is .draining.<new_epoch> — distinct from src.
            dst_path = _draining_path(_spool_path(f.pid), new_epoch)
            # Single atomic rename + unlink source. If rename fails, the
            # tmp file is cleaned up in the except branch.
            os.rename(str(tmp_path), str(dst_path))
            try:
                os.unlink(str(f.path))
            except OSError as e:  # pragma: no cover
                # Source gone (race / already cleaned); rename succeeded so
                # the remainder file is correctly in place.
                _breadcrumb(
                    f"phase5 src unlink after split failed: "
                    f"{type(e).__name__}: {e}"
                )
            stats.files_split_remainder += 1
        except OSError as e:
            _breadcrumb(f"phase5 split failed: {type(e).__name__}: {e}")
            try:
                if tmp_path.exists():
                    os.unlink(str(tmp_path))
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Journal post-drain compaction
# ---------------------------------------------------------------------------


def _journal_compact_drained(
    pid: int,
    drained_record_ids: Iterable[str],
    drain_epoch: str,
) -> None:
    """Append op=drained envelopes; rewrite journal dropping fully-completed triples.

    P1-3: emits op:"drained" envelopes with the actual record_id so
    session-start reconciliation can distinguish recovered from inflight.
    """
    drained_set = {r for r in drained_record_ids if isinstance(r, str) and r}
    if not drained_set:
        return
    # Flush any pending in-memory journal envelopes for this PID FIRST so
    # the compaction read sees a consistent on-disk view.
    _flush_journal_buffer(pid)
    journal = _journal_path(pid)
    if not journal.exists():
        return
    # 1) Append drained envelopes via the buffer (then flush)
    for rid in drained_set:
        _write_journal_envelope(
            pid, rid, "", -1, "", "drained", drain_epoch=drain_epoch,
        )
    _flush_journal_buffer(pid)
    # 2) Rewrite journal under per-PID journal flock dropping rows whose
    # record_id is in drained_set (begin/commit/drained triples collapse).
    try:
        with FileLock(_journal_flock_path(pid), timeout=SPOOL_LOCK_TIMEOUT):
            with journal.open("r", encoding="utf-8") as f:
                keep_lines: List[str] = []
                for raw in f:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    try:
                        env = json.loads(stripped)
                    except json.JSONDecodeError:
                        keep_lines.append(raw)
                        continue
                    if (isinstance(env, dict)
                            and env.get("record_id") in drained_set):
                        continue
                    keep_lines.append(raw)
            tmp = journal.with_name(journal.name + ".compact.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                f.writelines(keep_lines)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp), str(journal))
    except FileLockTimeout:
        _breadcrumb(f"journal compact flock timeout pid={pid}")
    except OSError as e:
        _breadcrumb(f"journal compact failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# drain_now — orchestration
# ---------------------------------------------------------------------------
