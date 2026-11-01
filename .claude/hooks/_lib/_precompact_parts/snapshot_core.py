"""Snapshot construction, plan discovery and persistence."""
from __future__ import annotations

def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_precompact_continuity: %s\n" % msg[:160])


def _sanitize_text(raw: str, clamp: int) -> str:
    """Disk-sourced strings written into the snapshot are kept printable-ASCII
    + clamped — the snapshot blob is later read by the PostCompact half and a
    control char / newline could distort downstream rendering. Mirrors the
    closeout-guard ``_sanitize_path`` hardening (Codex S228 P0)."""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in raw)
    return cleaned[:clamp]


def _git(
    args: List[str], cwd: str, timeout_s: float = 2.0, raw: bool = False
) -> str:
    """stdout on success, '' on any failure (fail-open).

    ``timeout_s`` (rail r2 P2-f): a caller under a shared wall deadline
    passes its REMAINING time — a fixed 2s here let a late call run past
    the hook budget. Existing call sites keep the historical default.

    Rail r8 P2-b: um resto de budget ABAIXO do floor de subprocess não é
    budget útil — o antigo ``max(0.05, ...)`` ESTICAVA um resto de 10ms
    para 50ms e furava o wall deadline compartilhado. Sem budget, a
    resposta honesta é o fail-open imediato, nunca uma chamada tardia."""
    if timeout_s < 0.05:
        return ""
    try:
        # Rail r10 P2-a: errors="replace" — filename nao-UTF-8 (legal em
        # Linux) sob `-z` vem em bytes crus; o decode ESTRITO do text=True
        # levantava UnicodeDecodeError que NENHUM except aqui pegava e o
        # snapshot inteiro morria por causa do indice OPCIONAL. Com
        # replacement o path vira U+FFFD, nao casa shape nenhum e degrada
        # honesto.
        p = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True,
            errors="replace", timeout=timeout_s,
        )
        if p.returncode != 0:
            return ""
        # Rail r11 P2-c: em modo raw (-z) o strip do output INTEIRO
        # corromperia whitespace legitimo do primeiro/ultimo path — os
        # limites exatos ja vem dos NULs.
        return p.stdout if raw else p.stdout.strip()
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


def _last_tag_time(cwd: str, timeout_s: float = 2.0) -> float:
    # Rail r21 P2-c: o caller sob deadline compartilhado passa o RESTO —
    # o default fixo de 2.0s somado a fatia do indice estourava o
    # TIME_BUDGET_S de 2.5s do gate num repositorio lento.
    out = _git(
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--count=1",
            "--format=%(creatordate:unix)",
            "refs/tags",
        ],
        cwd,
        timeout_s=timeout_s,
    )
    try:
        return float(out)
    except ValueError:
        return 0.0


def _ceremony_flags(cwd: str, deadline: float) -> List[str]:
    """Pending Owner-GPG ceremonies — executable finish-*.sh newer than the
    last tag (the closeout-guard's signal). Repo-relative, sanitized, sorted,
    bounded. These are POINTERS the operator must act on post-compaction."""
    tag_time = _last_tag_time(cwd, timeout_s=deadline - time.monotonic())
    found = set()
    patterns = (
        os.path.join(cwd, ".claude", "plans", "PLAN-*", "staged", "**", "finish-*.sh"),
        os.path.join(cwd, "scripts", "local", "finish-*.sh"),
    )
    for pattern in patterns:
        # Rail r22 P2-c: deadline ANTES de cada glob e iteracao LAZY —
        # glob.glob materializava a arvore inteira antes do primeiro
        # check interno e o 2o pattern rodava mesmo apos o break.
        if time.monotonic() > deadline:
            break
        for path in glob.iglob(pattern, recursive=True):
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


def _hmac_chain_breadcrumb(deadline: Optional[float] = None) -> Dict[str, Any]:
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

    # Rail r21 P2-c: a espera de lock respeita o deadline compartilhado —
    # sem resto de budget, leitura lockless direta (advisory sidecar; a
    # corrida de um evento e inofensiva, doutrina ja declarada acima).
    _lock_wait = 0.5
    if deadline is not None:
        _lock_wait = min(0.5, deadline - time.monotonic())
    if _have_lock and FileLock is not None and _lock_wait > 0:
        try:
            lock_path = audit_hmac.last_hmac_path().with_name("audit-log.lock")
            with FileLock(lock_path, timeout=_lock_wait):
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
