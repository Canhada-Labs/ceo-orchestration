#!/usr/bin/env python3
"""PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PreCompact governance
snapshot.

Compaction is the OTHER way a session's protocol state dies — the
closeout-guard (S228) covers only Stop. When the Claude Code harness fires
``PreCompact`` (manual ``/compact`` or auto context-window threshold), this
hook snapshots, into the plan-scoped scratchpad, the governance state the
post-compaction transcript would otherwise forget:

  - ``plan_id`` — the PLAN-NNN currently scoped to the session (derived from
    the audit-log ``plan_transition`` events, NOT an env var — agent-spoofable;
    scratchpad_lib.resolve_plan_id doctrine);
  - ``execution_unit`` — the active execution-unit position (the first
    unchecked ``- [ ]`` checkbox in the current plan file, repo-relative path
    + line + sanitized label);
  - ``ceremony_flags`` — pending Owner-GPG ceremony breadcrumbs (executable
    ``finish-*.sh`` under ``staged/**`` / ``scripts/local/`` newer than the
    last git tag — the closeout-guard's signal, reused);
  - ``hmac_chain`` — a READ-ONLY breadcrumb of the audit HMAC-chain state
    (last-hmac hex PREFIX + chain-length counter) so a post-compaction
    integrity check has the pre-compaction anchor.

The matching ``PostCompact`` hook (``check_postcompact_reinject.py``) reads
this snapshot back and reinjects governance POINTERS (not the snapshot body)
via ``additionalContext``.

## PLAN-179 W1 US3 — session-scope fallback (the ADR-153 fires-proof cure)

The S309 fires-proof was NEGATIVE for the dominant path: ``resolve_plan_id``
needs a ``plan_transition`` event *from this same session*, and a real session
emits ~0 of those (2 events in 12.515 log lines), so every long session — the
only kind that ever compacts — snapshotted NOTHING. The write is no longer
skipped when the plan is unresolved: it goes to a SESSION-scoped store
(``scratchpad_lib.open_session_scratchpad``) and reports the new outcome
``written_session_scope``. Per emenda r1-C1 the session id comes ONLY from the
hook input — if the derivation would fall back to ``CLAUDE_SESSION_ID`` (env,
agent-spoofable — consensus M2) the fallback is REFUSED and the outcome stays
``scratchpad_unavailable``; the scope is recorded in the blob's own
``scope_kind`` field, never by overloading ``plan_id`` (the store's
plan-isolation invariant stays intact).

## Contract

- ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing files /
  derivation failures / timeouts → stderr breadcrumb + emit ``{}``). NEVER
  blocks — a crashed snapshot must not stop a compaction.
- Time budget ``TIME_BUDGET_S`` (subprocess git capped; budget-blown → snapshot
  what we have, never noise).
- Emits ONE closed-enum ``compaction_continuity_snapshot`` audit event
  (registered in BOTH ``_KNOWN_ACTIONS`` and SPEC v2.43) carrying ONLY closed
  enums + counters: ``trigger`` (manual/auto/other), ``snapshot_outcome``
  (written/written_session_scope/scratchpad_unavailable/error/other),
  ``plan_id`` (PLAN-NNN or ``unknown``), ``chain_length`` (clamped int). The
  snapshot BODY (plan path text, checkbox label, ceremony paths, last-hmac
  hex) is written to the scratchpad — NEVER to the audit wire.
- Snapshot privacy: the write is plan- or session-scoped and secrets-redacted
  by ``state_store.set``; the audit emit carries no path/label text.
  **PLAN-179 amendment 8.3 (debate C9):** this claim used to be FALSE on the
  path actually taken — ``state_store.set`` redacts ``isinstance(value, str)``
  ONLY and this hook handed it ``payload.encode("utf-8")``, i.e. bytes, which
  the store trusts verbatim. The snapshot is now passed as a ``str`` so the
  store's own redactor runs. Same rule for the session-scoped write.
- Kill-switch: ``CEO_COMPACTION_CONTINUITY=0`` (shared with the PostCompact
  reinjection half). It also disables the session-store GC below — the switch
  turns the whole feature off, housekeeping included.
- PLAN-179 rail finding C: this hook is the PRODUCTION CALLER of
  ``scratchpad_lib.gc_orphan_session_stores`` (see ``_gc_session_stores``).
  The session-scope fallback creates one sqlite store per unresolved-plan
  session and row-TTL expiry cannot unlink a FILE, so without a caller the
  fallback accumulated files without bound. The sweep runs last, is bounded by
  the library's own per-run cap, respects the remaining time budget and is
  fail-open: no snapshot outcome depends on it.
- PLAN-179 W0 US2b progress guard: OBSERVE + NOTIFY only (see
  ``_progress_guard``); it emits ``context_pressure_observed`` and a stderr
  breadcrumb, and is DISABLED unless ``CEO_CONTEXT_PROGRESS_FLOOR_TOKENS`` is
  set. It cannot halt a compaction — PreCompact has no deny channel.
- Stdlib only, Python >= 3.9.

## Scratchpad key

``compaction_continuity`` (single JSON blob, <64 KiB; ``set`` overwrites). The
PostCompact half reads this exact key — in the plan scope first, then (PLAN-179
W1 US3) in the session scope.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Make the local `_lib` importable (matches the pattern of existing hooks).
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

TIME_BUDGET_S = 2.5
SCRATCHPAD_KEY = "compaction_continuity"
MAX_CEREMONY_FLAGS = 5
# Snapshot blob is capped well under the scratchpad 64 KiB per-key limit; the
# label/path clamps below keep it small regardless.
_LABEL_CLAMP = 160
_PATH_CLAMP = 200

# PLAN-179 W1 US3 / emenda r1-C2 — the session-scoped store is created per
# session id, so it accumulates files the plan-scoped one does not. Every
# session-scope write carries an EXPLICIT ttl so an orphaned snapshot expires
# on its own even before the file-level GC item ships. Hygiene value (7 days),
# not a decision-bearing number.
SESSION_SNAPSHOT_TTL_S = 7 * 24 * 3600

# PLAN-179 W0 US2b — progress-guard floor. The plan's own words: "requer o `F`
# medido acima; até lá o piso não tem valor honesto". So there is NO default
# here: absent/malformed env => the guard is a NO-OP. Once W0 measures F and T
# the operator sets the env var; a literal default would be a magic number
# shipped ahead of its measurement.
PROGRESS_FLOOR_ENV = "CEO_CONTEXT_PROGRESS_FLOOR_TOKENS"

# PLAN-179 W0 US2b / amendment 8.1 — WIRE CONTRACT for `context_pressure_observed`.
#
# INTEGRATION DEFECT CLOSED HERE (PLAN-179 W0/W1 cross-file pass): this hook
# used to compute a TOKEN-COUNT bucket (`used_tokens // 10000`, clamped 999)
# and emit it as `used_tokens_bucket=` alongside `floor_tokens=`. Neither field
# name exists in `_lib/audit_emit._CONTEXT_PRESSURE_OBSERVED_ALLOWLIST`, whose
# scrub is DENY-BY-DEFAULT — so both were dropped and every emit landed as a
# bare `used_bucket=0`. The wire field is `used_bucket` and it is a COARSE
# INTEGER PERCENT rung (share of the context window consumed), never a raw or
# token-derived count: a raw count is a transcript-size side channel, and a
# FLOAT under the HMAC chain discards the WHOLE event
# ([[feedback-float-in-hmac-field-drops-whole-event]]).
#
# The rung SET is DERIVED from audit_emit at call time, never restated here
# ([[feedback-closed-sets-must-be-derived-not-recalled]]): a literal copy would
# drift from the scrub branch that validates it and the event would coerce to
# the 0 sentinel forever, i.e. exactly the silent dead instrument this pass
# exists to remove.
_PRESSURE_RUNGS_ATTR = "_CONTEXT_PRESSURE_USED_BUCKETS_PCT"
# This producer's value inside audit_emit._CONTEXT_PRESSURE_EVENT_SOURCES.
_PRESSURE_EVENT_SOURCE = "precompact"
# audit_emit's documented "unrecognized / absent bucket" sentinel — deliberately
# OUTSIDE the percent enum so a consumer can always tell a real rung from a
# coerced one. Emitted when the hook input carries no context-window accounting.
_PRESSURE_BUCKET_UNKNOWN = 0
# `should_emit_context_pressure(used_bucket, state_dir)` keeps its edge-trigger
# marker under `<project>/.claude/state` (its own docstring names that path).
_PRESSURE_STATE_SUBPATH = (".claude", "state")

# Candidate shapes for the harness's context-window accounting. These MIRROR
# `.claude/scripts/statusline-ceo.py:context_pct()` — the one place in this repo
# that already reverse-engineered the harness payload — rather than being
# guessed here. Absent ⇒ no percent is invented
# ([[feedback-measurement-must-list-its-inputs]]).
_CONTEXT_WINDOW_KEYS = ("context_window", "context", "context_usage")
_CONTEXT_PCT_KEYS = ("used_percentage", "used_pct", "percent_used")
_CONTEXT_USED_KEYS = ("used_tokens", "input_tokens", "total_input_tokens")
_CONTEXT_SIZE_KEYS = ("context_window_size", "max_tokens", "size")


def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_precompact_continuity: %s\n" % msg[:160])


def _sanitize_text(raw: str, clamp: int) -> str:
    """Disk-sourced strings written into the snapshot are kept printable-ASCII
    + clamped — the snapshot blob is later read by the PostCompact half and a
    control char / newline could distort downstream rendering. Mirrors the
    closeout-guard ``_sanitize_path`` hardening (Codex S228 P0)."""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in raw)
    return cleaned[:clamp]


def _git(args: List[str], cwd: str) -> str:
    """stdout on success, '' on any failure (fail-open)."""
    try:
        p = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=2
        )
        return p.stdout.strip() if p.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _resolve_project_root(cwd: str) -> str:
    """Project ROOT for every path this hook derives (rail round-9 [P2]).

    O ``cwd`` do hook-input segue o CwdChanged da sessão para
    subdiretórios; derivar `.claude/...` dele fragmenta o estado — o
    lookup de plano erra, e o marker de pressão ganha uma cópia por
    subdiretório, derrotando o contrato de histerese. A autoridade é o
    toplevel do git (lição feedback-guard-must-resolve-repo-by-git-toplevel);
    o fallback sobe até o ancestral mais próximo com `.claude/`, e falha
    de resolução mantém o cwd (degradado, nunca quebrado)."""
    # Walk-up PRIMEIRO (não git-first): o leitor do marker no PostCompact
    # tem contrato no-exec e só pode usar o walk-up — para escritor e
    # leitor concordarem em TODO caso decisivo, a regra primária dos dois
    # é idêntica. O git-toplevel fica como fallback para o caso sem
    # `.claude/` em ancestral algum (onde não há marker a re-armar).
    probe = os.path.realpath(cwd)
    while True:
        if os.path.isdir(os.path.join(probe, ".claude")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    top = _git(["rev-parse", "--show-toplevel"], cwd)
    if top and os.path.isdir(top):
        return os.path.realpath(top)
    return os.path.realpath(cwd)


def _trigger_class(event: Dict[str, Any]) -> str:
    """Map the harness PreCompact trigger to the closed enum.

    The documented PreCompact hook input carries a ``trigger`` field with
    ``manual`` (user ran /compact) or ``auto`` (context-window threshold).
    Anything else (incl. a missing field on a future harness change) is
    ``other`` — the audit_emit scrub re-coerces too (defense in depth)."""
    val = event.get("trigger")
    if val in ("manual", "auto"):
        return val
    return "other"


def _resolve_plan_id(event: Dict[str, Any]) -> str:
    """Derive PLAN-NNN from the audit log (NOT env — agent-spoofable).

    Returns ``unknown`` on any derivation failure (fail-open; the snapshot is
    still written with what we have)."""
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("scratchpad_lib import failed (%s)" % str(exc)[:60])
        return "unknown"
    session_id = None
    sid = event.get("session_id") or event.get("sessionId")
    if isinstance(sid, str) and sid.strip():
        session_id = sid.strip()
    try:
        return scratchpad_lib.resolve_plan_id(session_id)
    except Exception as exc:
        _breadcrumb("plan_id derivation failed (%s)" % str(exc)[:80])
        return "unknown"


def _session_scope_id(event: Dict[str, Any]) -> Optional[str]:
    """Session id usable as a WRITE SCOPE, or None (PLAN-179 W1 US3, r1-C1).

    Delegates the shape validation + the provenance rule to
    ``scratchpad_lib.session_id_from_event``: the id must come from the HOOK
    INPUT. If that helper returns None — no id in the event, malformed shape,
    or an id that would have been sourced from ``CLAUDE_SESSION_ID`` (env is
    agent-spoofable, consensus M2) — we REFUSE the fallback rather than write
    under a scope an agent could have chosen. Import/derivation failure is
    infrastructure: breadcrumb + None (fail-open)."""
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("scratchpad_lib import failed at session scope (%s)" % str(exc)[:60])
        return None
    try:
        sid = scratchpad_lib.session_id_from_event(event)
    except Exception as exc:
        _breadcrumb("session scope derivation failed (%s)" % str(exc)[:80])
        return None
    if isinstance(sid, str) and sid.strip():
        return sid.strip()
    # None here is a DECISION (env-sourced / absent / malformed), not an error.
    return None


def _plan_file_for(plan_id: str, cwd: str) -> Optional[str]:
    """Absolute path of the plan markdown file for ``plan_id``, or None.

    Matches ``PLAN-NNN-*.md`` directly under ``.claude/plans/`` (PLAN-SCHEMA
    naming). Returns the first match in sorted order (deterministic)."""
    if not plan_id.startswith("PLAN-"):
        return None
    pattern = os.path.join(cwd, ".claude", "plans", plan_id + "-*.md")
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None


def _execution_unit(plan_path: Optional[str], cwd: str, deadline: float) -> Dict[str, Any]:
    """First unchecked ``- [ ]`` checkbox in the plan file (the active unit).

    Returns ``{}`` when no plan file / no unchecked unit / budget blown.
    Path is repo-relative + sanitized; label is sanitized + clamped. The
    snapshot records position only — never the plan body."""
    if not plan_path:
        return {}
    try:
        rel = _sanitize_text(os.path.relpath(plan_path, cwd), _PATH_CLAMP)
    except (OSError, ValueError):
        rel = _sanitize_text(plan_path, _PATH_CLAMP)
    try:
        with open(plan_path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, start=1):
                if time.monotonic() > deadline:
                    return {}
                stripped = line.lstrip()
                # Unchecked checkbox, tolerant of leading list whitespace.
                if stripped.startswith("- [ ]"):
                    label = stripped[len("- [ ]"):].strip()
                    return {
                        "plan_path": rel,
                        "line": lineno,
                        "label": _sanitize_text(label, _LABEL_CLAMP),
                    }
    except OSError as exc:
        _breadcrumb("plan file read failed (%s)" % str(exc)[:60])
        return {"plan_path": rel}
    # All checkboxes checked (or none): record the file, no active unit.
    return {"plan_path": rel}


def _last_tag_time(cwd: str) -> float:
    out = _git(
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--count=1",
            "--format=%(creatordate:unix)",
            "refs/tags",
        ],
        cwd,
    )
    try:
        return float(out)
    except ValueError:
        return 0.0


def _ceremony_flags(cwd: str, deadline: float) -> List[str]:
    """Pending Owner-GPG ceremonies — executable finish-*.sh newer than the
    last tag (the closeout-guard's signal). Repo-relative, sanitized, sorted,
    bounded. These are POINTERS the operator must act on post-compaction."""
    tag_time = _last_tag_time(cwd)
    found = set()
    patterns = (
        os.path.join(cwd, ".claude", "plans", "PLAN-*", "staged", "**", "finish-*.sh"),
        os.path.join(cwd, "scripts", "local", "finish-*.sh"),
    )
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if time.monotonic() > deadline:
                break
            try:
                if os.access(path, os.X_OK) and os.path.getmtime(path) > tag_time:
                    found.add(
                        _sanitize_text(os.path.relpath(path, cwd), _PATH_CLAMP)
                    )
            except OSError:
                continue
    return sorted(found)[:MAX_CEREMONY_FLAGS]


def _hmac_chain_breadcrumb() -> Dict[str, Any]:
    """READ-ONLY snapshot of the HMAC-chain anchor: last-hmac hex PREFIX +
    chain-length counter.

    Lock-respecting (audit_hmac readers MUST hold the audit filelock — we take
    a best-effort shared lock; on unavailability we still read, since these are
    advisory sidecars and a one-event race is harmless for a snapshot anchor).
    Returns ``{"chain_length": 0}`` on any failure (fail-open). Only the FIRST
    12 hex chars of the last-hmac are kept — enough to detect a post-compaction
    chain divergence, not enough to be a forgery oracle."""
    out: Dict[str, Any] = {"chain_length": 0, "last_hmac_prefix": ""}
    try:
        from _lib import audit_hmac  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("audit_hmac import failed (%s)" % str(exc)[:60])
        return out
    try:
        from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
        _have_lock = True
    except Exception:  # pragma: no cover
        FileLock = None  # type: ignore[assignment]
        FileLockTimeout = Exception  # type: ignore[assignment, misc]
        _have_lock = False

    def _read() -> None:
        try:
            out["chain_length"] = int(audit_hmac.read_chain_length())
        except Exception:
            out["chain_length"] = 0
        try:
            prev = audit_hmac.read_prev_hmac()
            out["last_hmac_prefix"] = audit_hmac.hex_digest(prev)[:12]
        except Exception:
            out["last_hmac_prefix"] = ""

    if _have_lock and FileLock is not None:
        try:
            lock_path = audit_hmac.last_hmac_path().with_name("audit-log.lock")
            with FileLock(lock_path, timeout=0.5):
                _read()
            return out
        except FileLockTimeout:
            _breadcrumb("hmac sidecar lock timeout — lockless best-effort read")
        except Exception as exc:
            _breadcrumb("hmac sidecar lock error (%s) — lockless read" % str(exc)[:60])
    _read()
    return out


def _emit_snapshot_event(
    trigger: str, plan_id: str, chain_length: int, snapshot_outcome: str
) -> None:
    """Emit the closed-enum compaction_continuity_snapshot breadcrumb.

    Carries ONLY closed enums + the chain_length counter — never the snapshot
    body. Import-guarded; any failure is swallowed (the hook NEVER blocks on
    audit infra). Mirrors the check_protocol_semver_cascade emit idiom."""
    try:
        from _lib import audit_emit  # noqa: E402
    except Exception:
        return
    try:
        audit_emit.emit_generic(
            action="compaction_continuity_snapshot",
            trigger=trigger,
            plan_id=plan_id,
            chain_length=chain_length,
            snapshot_outcome=snapshot_outcome,
        )
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("audit emit failed (%s)" % str(exc)[:80])


def _write_snapshot(
    plan_id: str, blob: Dict[str, Any], session_id: Optional[str] = None
) -> str:
    """Persist the snapshot blob to the plan- or session-scoped scratchpad.

    Returns the closed-enum snapshot_outcome:

      - ``written`` — plan scope resolved, blob written under ``plan_id``;
      - ``written_session_scope`` — PLAN-179 W1 US3: no plan scope, but the
        hook input carried a usable session id, so the blob was written under
        the SESSION store (``scope_kind="session"`` inside the blob; the
        ``plan_id`` field is left at ``unknown`` — emenda r1-C1 forbids
        overloading it, the store's plan-isolation invariant depends on it);
      - ``scratchpad_unavailable`` — a REAL unavailability: the scratchpad_lib
        import failed, or there is no scope we are allowed to write under
        (session id absent / malformed / env-sourced ⇒ refused, r1-C1). It no
        longer means "the plan was not resolved" — that case now WRITES;
      - ``error`` — serialization or the store write itself failed.

    Secrets: the blob is handed to ``store.set`` as a ``str`` on BOTH paths so
    the store's ``redact_secrets`` pass actually runs (PLAN-179 amendment 8.3
    / debate C9 — the previous ``payload.encode("utf-8")`` took the bytes
    branch, which ``state_store`` trusts verbatim, making the documented
    "secrets-redacted" claim false on the only path this hook used).
    ``set`` overwrites the prior snapshot in either scope."""
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:
        _breadcrumb("scratchpad_lib import failed at write (%s)" % str(exc)[:60])
        return "scratchpad_unavailable"

    plan_scoped = plan_id != "unknown" and plan_id.startswith("PLAN-")
    if not plan_scoped and not session_id:
        # No scope we may write under: the plan is unresolved AND the session
        # id was absent/malformed/env-sourced. The audit event still records
        # the attempt (PostCompact degrades to snapshot_found=False).
        _breadcrumb("no plan scope and no hook-input session id — write skipped")
        return "scratchpad_unavailable"

    # scope_kind travels INSIDE the blob (r1-C1) so the PostCompact half can
    # tell a session-scoped snapshot from a plan-scoped one without guessing.
    #
    # PLAN-179 W0/W1 cross-file pass — closes the "recalled closed set" defect:
    # this used to write the literal strings "plan"/"session". The enum's owner
    # is scratchpad_lib (SCOPE_KIND_PLAN / SCOPE_KIND_SESSION, validated by
    # stamp_scope_kind, which RAISES on an off-enum value). Stamping through the
    # library means a future rename cannot leave this writer emitting a value
    # the PostCompact reader no longer recognises
    # ([[feedback-closed-sets-must-be-derived-not-recalled]]).
    body = dict(blob)
    try:
        scope_kind = (
            scratchpad_lib.SCOPE_KIND_PLAN
            if plan_scoped
            else scratchpad_lib.SCOPE_KIND_SESSION
        )
        scratchpad_lib.stamp_scope_kind(body, scope_kind)
    except Exception as exc:
        # AttributeError = an adopter on a pre-PLAN-179 scratchpad_lib (the only
        # genuine cross-version case); ValueError = an off-enum scope_kind, which
        # would be a bug in THIS file. Either way the snapshot is still worth
        # writing, but it MUST carry the field the PostCompact reader keys on —
        # so fall back to the literal and say loudly that the library did not
        # own the enum on this run.
        _breadcrumb(
            "scratchpad_lib scope-kind API unavailable/refused (%s) — "
            "stamping scope_kind inline; expected the library to own this enum"
            % str(exc)[:60]
        )
        body["scope_kind"] = "plan" if plan_scoped else "session"
    # Rail round-8 [P1]: redaction is a FIELD-level duty here, not a
    # store-level one. `state_store.set` runs `redact_secrets` over str
    # values, and its kv pattern (`token=\S{1,2048}`) is JSON-blind: on a
    # serialized snapshot whose field ends in assignment-shaped text
    # (`deploy token=abc`) it consumes the closing quote/comma and stores
    # MALFORMED JSON — PostCompact parses nothing and the continuity cure
    # dies silently for exactly the secrets it must survive. So every str
    # field is redacted BEFORE serialization (max_chars=0, no truncation)
    # and the store receives BYTES — its documented "caller owns the
    # content" route (amendment 8.3's redaction CLAIM stays true; only the
    # layer that fulfils it moved). If the redactor is unavailable, fall
    # back to the old str path: the store's pass still guarantees nothing
    # unredacted lands on disk (the residual cost is the corruption this
    # cure removes — never a secret).
    try:
        from _lib.redact import redact_secrets as _redact_fn
    except Exception:
        _redact_fn = None
    if _redact_fn is not None:
        def _redact_tree(node):
            if isinstance(node, str):
                return _redact_fn(node, max_chars=0)
            if isinstance(node, dict):
                return {k: _redact_tree(v) for k, v in node.items()}
            if isinstance(node, list):
                return [_redact_tree(v) for v in node]
            return node
        try:
            body = _redact_tree(body)
        except Exception as exc:
            _breadcrumb("snapshot field redaction failed (%s)" % str(exc)[:60])
            _redact_fn = None

    try:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        _breadcrumb("snapshot serialize failed (%s)" % str(exc)[:60])
        return "error"
    store_value = (
        payload.encode("utf-8") if _redact_fn is not None else payload
    )

    try:
        if plan_scoped:
            with scratchpad_lib.open_scratchpad(plan_id=plan_id) as store:
                store.set(SCRATCHPAD_KEY, store_value)
            return "written"
        with scratchpad_lib.open_session_scratchpad(session_id) as store:
            # Explicit ttl (emenda r1-C2): session scopes are per-session and
            # would otherwise accumulate forever.
            #
            # PLAN-179 W0/W1 cross-file pass: routed through the library's
            # `set_session_value` rather than `store.set(..., ttl_seconds=...)`.
            # That helper is where r1-C2 made the positive TTL MECHANICAL — it
            # RAISES on a None/non-positive ttl instead of silently writing a
            # never-expiring row, which is precisely the accumulation bug the
            # amendment named. Calling store.set directly bypassed the guard the
            # library exists to provide.
            scratchpad_lib.set_session_value(
                store, SCRATCHPAD_KEY, store_value,
                ttl_seconds=SESSION_SNAPSHOT_TTL_S,
            )
        return "written_session_scope"
    except Exception as exc:
        _breadcrumb("scratchpad write failed (%s)" % str(exc)[:80])
        return "error"


def _gc_session_stores(deadline: float) -> None:
    """Reclaim aged-out session-store FILES. Never affects the snapshot.

    PLAN-179 rail finding C (round-1 REJECT): ``gc_orphan_session_stores`` had
    no production caller anywhere in the tree, so the W1 US3 session-scope
    fallback accumulated one ``session-<uuid>.sqlite`` (+ ``.lock`` / WAL /
    SHM) per unresolved-plan session with nothing to reclaim it — row TTL
    expiry cannot unlink a file. This is that caller.

    Three properties, in the order they matter:

    1. **Fail-OPEN, always.** Import failure, a missing symbol on a
       pre-PLAN-179 adopter, any exception out of the sweep: breadcrumb and
       return. The snapshot above it has already been written and its outcome
       is already on the wire — housekeeping may not retro-actively change it.
    2. **Cheap and bounded.** PreCompact fires at most once per compaction, so
       no extra throttle is invented here (a timestamp file would be a second
       piece of state to get wrong). The work is one directory listing plus at
       most ``MAX_GC_FILES_PER_RUN`` unlinks — the cap is the LIBRARY's, not
       a number recalled here
       ([[feedback-closed-sets-must-be-derived-not-recalled]]). The remaining
       budget is honoured: a run that already blew ``TIME_BUDGET_S`` skips the
       sweep rather than adding to the overrun.
    3. **TTL matched to what this hook WRITES.** ``ttl_seconds`` is passed
       explicitly as :data:`SESSION_SNAPSHOT_TTL_S` (7 days) because the
       library default is 72h, and a 72h mtime cutoff would unlink a store
       whose rows this hook wrote with a 7-day TTL — deleting a snapshot that
       is still live. The GC threshold must never be shorter than the write
       TTL it collects behind."""
    if time.monotonic() > deadline:
        _breadcrumb("time budget spent — session-store GC skipped this run")
        return
    try:
        from _lib import scratchpad_lib  # noqa: E402
    except Exception as exc:
        _breadcrumb("scratchpad_lib import failed at GC (%s)" % str(exc)[:60])
        return
    gc = getattr(scratchpad_lib, "gc_orphan_session_stores", None)
    if gc is None:
        _breadcrumb(
            "scratchpad_lib.gc_orphan_session_stores missing — this build "
            "predates PLAN-179 W1 US3; session-store GC skipped"
        )
        return
    try:
        removed = gc(ttl_seconds=SESSION_SNAPSHOT_TTL_S)
    except Exception as exc:
        # The helper documents itself as fail-open, so an exception here is a
        # genuine surprise — still swallowed: this runs AFTER the snapshot.
        _breadcrumb("session-store GC failed (%s) — ignored" % str(exc)[:80])
        return
    if removed:
        _breadcrumb("session-store GC unlinked %d aged-out file(s)" % removed)


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
    the actual valve stays a W1+ item on a surface that owns a decision.

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
        "ceremony_flags": _ceremony_flags(cwd, deadline),
        "hmac_chain": _hmac_chain_breadcrumb(),
    }
    chain_length = 0
    try:
        chain_length = int(blob["hmac_chain"].get("chain_length", 0))
    except (TypeError, ValueError, AttributeError):
        chain_length = 0
    outcome = _write_snapshot(plan_id, blob, session_id)
    _emit_snapshot_event(trigger, plan_id, chain_length, outcome)
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


if __name__ == "__main__":
    main()
