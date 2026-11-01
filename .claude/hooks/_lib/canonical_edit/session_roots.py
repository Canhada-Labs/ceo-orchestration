"""Session workspace registry and external write protection.

Functions are bound to the owning hook namespace by ``bind``. This keeps
its injectable dependencies and per-import state on the public hook.
"""
from __future__ import annotations

__all__ = ('_session_roots_registry_path', '_session_roots_partition_external', '_session_roots_guard', '_audit_registry_unreadable', '_audit_session_root_block')


def _session_roots_registry_path(repo_root: Path) -> Path:
    """Location of the session-roots registry written by the B1 observer."""
    return repo_root / ".claude" / "state" / "session-roots.json"



def _session_roots_partition_external(
    candidate_paths: List[str],
    repo_root: Path,
) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """Partition event write-targets into repo-internal vs external.

    Shared canonicalization core for ``_session_roots_guard``: used by BOTH
    the active-guard path (registry parsed, roots registered for this
    session) AND the corrupt-registry fail-CLOSED branch (FXγ / C3), so the
    two call sites agree byte-for-byte on what counts as an EXTERNAL write.
    A single source of truth here is a cross-state safeguard: it stops the
    corrupt-branch and the active-path external-detection from drifting apart
    and disagreeing on the same tool-input.

    Returns ``(uncanon_reason, external)``:
      * ``uncanon_reason`` is a fail-CLOSED block-reason string when ANY
        candidate cannot be canonicalized (not a str, empty, embedded NUL,
        or ``os.path.realpath`` raised). A path that cannot be proven
        repo-internal must not be waved through while a session-roots
        security condition is in force. ``external`` is ``[]`` in that case.
      * otherwise ``uncanon_reason`` is ``None`` and ``external`` lists the
        ``(original, realpath)`` pairs that resolve OUTSIDE ``repo_root``
        (repo-internal candidates are governed by the canonical stack above
        and are dropped here). If ``repo_root`` itself cannot be
        canonicalized, NO candidate can be proven internal → every candidate
        is treated as external (fail-CLOSED on an unknowable boundary).

    Pure: no emission, no raises out (realpath failures are caught and
    converted to the fail-CLOSED ``uncanon_reason`` return VALUE).
    """
    try:
        repo_rp = os.path.realpath(str(repo_root))  # type: Optional[str]
    except Exception:
        repo_rp = None

    external = []  # type: List[Tuple[str, str]]
    for cand in candidate_paths:
        # NUL/empty/non-str rejection is EXPLICIT (mirrors the control-char
        # rejection in _parse_scope_paths_from_text): since bpo-33721
        # (Py 3.8) os.path.realpath swallows the embedded-NUL ValueError and
        # returns the tainted string un-resolved, so the except branch below
        # never sees it — yet a NUL-bearing path is exactly the "cannot be
        # canonicalized" input class this matcher fail-CLOSES.
        if not isinstance(cand, str) or not cand or "\x00" in cand:
            return (_SESSION_ROOTS_UNCANON_EMPTY, [])
        try:
            rp = os.path.realpath(cand)
        except Exception:
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_path_uncanonicalizable "
                f"— write-target path {cand!r} cannot be canonicalized "
                "(os.path.realpath raised) while session-registered workspace "
                "roots are active. Security-matcher input → fail-closed "
                "(CLAUDE.md §4; PLAN-163 T3.1 / ADR-183).",
                [],
            )
        if repo_rp is not None and (
            rp == repo_rp or rp.startswith(repo_rp + os.sep)
        ):
            continue  # repo-internal → governed by the canonical stack above
        external.append((cand, rp))
    return (None, external)



def _session_roots_guard(
    candidate_paths: List[str],
    repo_root: Path,
    session_id: str,
    env=None,
) -> Optional[str]:
    """Pure deny predicate for writes under session-registered roots.

    Returns a block-reason string (→ deny) or ``None`` (→ allow). The DENY
    path is PURE in the ``_candidate_is_granted`` sense: no emission side
    effects — the deny audit breadcrumb is a once-per-event concern owned
    by ``main()``. The ONE carve-out is the corrupt / unreadable /
    unknown-schema registry branch: a PRESENT-but-unparseable registry is a
    security-matcher INPUT-parse failure (FXγ / C3), so it fails CLOSED for
    external writes (deny) while allowing repo-internal writes, and it
    additionally fires a best-effort tamper audit event (H5 observability,
    see below) so a registry-rewrite attack is both blocked and visible.
    ``env`` defaults to ``os.environ`` (injectable for tests).

    Deny returns are VALUES, never raises: an unexpected raise out of this
    function is a hook bug (INFRA) and the ``main()`` call site fail-OPENs
    it with a breadcrumb, per the CLAUDE.md §4 split.
    """
    src_env = env if env is not None else os.environ

    # ---- Load registry (absent OR infra-read-error → silent allow;
    # ---- present-but-unparseable → fail-CLOSED for external writes) ----
    registry_path = _session_roots_registry_path(repo_root)
    try:
        if not registry_path.is_file():
            return None
    except OSError:
        return None
    # C3 (codex/grok R4+R5): read raw BYTES in a SEPARATE try — an OSError here
    # (PermissionError, IsADirectory, transient IO) is an INFRASTRUCTURE read
    # failure, NOT tampering, so it fails OPEN (allow), same as an ABSENT file.
    # Folding it into the parse `except Exception` below turned an infra read
    # error into a fail-CLOSED external-write DENY — a self-DoS. Reading BYTES
    # (not text) keeps the utf-8 DECODE inside the fail-closed parse block:
    # non-utf-8 bytes raise UnicodeDecodeError (IS-A ValueError, NOT OSError),
    # which is PRESENT-but-unparseable security-matcher input and MUST
    # fail-CLOSED — an earlier `read_text(encoding=...)` let that escape to the
    # caller's infra catch-all and wrongly ALLOW a binary registry overwrite
    # (R5). Only an OSError (bytes not readable at all) is INFRA -> allow.
    try:
        raw_bytes = registry_path.read_bytes()
    except OSError:
        return None
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("registry root is not an object")
        if data.get("schema") != _SESSION_ROOTS_SCHEMA:
            raise ValueError("unknown registry schema")
        sessions = data.get("sessions")
        if not isinstance(sessions, dict):
            raise ValueError("registry 'sessions' is not an object")
    except Exception as exc:  # registry PRESENT + readable but unparseable
        print(
            "[check_canonical_edit] session-roots registry unreadable "
            f"({type(exc).__name__}); present-but-unparseable security-matcher "
            "input → fail-CLOSED for external writes; repo-internal writes stay "
            f"governed by the canonical stack. registry={registry_path}",
            file=sys.stderr,
        )
        # FXγ (C3) — DOCTRINE CORRECTION. A registry that EXISTS but cannot be
        # parsed (corrupt JSON, unknown schema-version, malformed `sessions`)
        # is PRESENT-but-unparseable security-matcher input, NOT an
        # ABSENT-file INFRA condition, so per CLAUDE.md §4 it fails CLOSED —
        # content the guard cannot parse is blocked, never waved through. The
        # deny is SCOPED to writes we cannot prove repo-internal (the new
        # surface an added root could have opened); repo-internal writes stay
        # governed by the canonical stack above (unaffected). Registry ABSENT
        # (handled earlier) remains an allow — the observer may simply not
        # have run.
        #
        # H5 observability is preserved and now UNCONDITIONAL: whether or not
        # this event carries an external write, the corruption is recorded in
        # the HMAC audit chain so a registry-rewrite attack leaves a forensic
        # trace. Emitted BEFORE the partition so even the allow (repo-internal
        # only) branch records the tamper. Best-effort; never raises.
        _audit_registry_unreadable(registry_path, type(exc).__name__)
        uncanon_reason, external = _session_roots_partition_external(
            candidate_paths, repo_root
        )
        if uncanon_reason is not None or external:
            # At least one write-target cannot be proven repo-internal while
            # the registry — the very state that tells us whether a root was
            # added — is unparseable. The write boundary is unknowable →
            # deny fail-CLOSED until the registry is repaired.
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_roots_registry_unreadable "
                "— the session-roots registry "
                "(.claude/state/session-roots.json) is PRESENT but could not be "
                "parsed (corrupt JSON, unknown schema-version, or a malformed "
                "'sessions' object). A present-but-unparseable security-matcher "
                "input cannot prove this write stays inside the project root, "
                "so writes OUTSIDE the repo are denied fail-closed (CLAUDE.md "
                "§4) until the registry is repaired or removed. Repo-internal "
                "writes remain governed by the canonical stack; the corruption "
                "is recorded in the HMAC audit chain. PLAN-163 T3.1 / ADR-183; "
                "H5."
            )
        return None  # all writes provably repo-internal → canonical stack

    sid = (session_id or "").strip()
    # M1 (PLAN-163 T3.1 / ADR-183) — an ABSENT/empty session_id while the
    # registry holds registered sessions is a security-matcher input the
    # guard cannot bind to a session, yet roots DO exist → the write
    # boundary is unknowable → fail-CLOSED (CLAUDE.md §4). Denying here
    # means clearing CLAUDE_SESSION_ID cannot silently neutralize the
    # guard. Only EXTERNAL writes are denied (repo-internal writes stay
    # governed by the canonical stack above); the deny is emitted below,
    # after the fail-CLOSED input resolution, once ``external`` is known.
    sid_missing_with_registry = (not sid) and bool(sessions)
    if sid_missing_with_registry:
        roots = []  # boundary unknowable; external writes denied below
    else:
        sess = sessions.get(sid)
        if not isinstance(sess, dict):
            return None  # no roots registered for THIS session
        roots = sess.get("roots")
        if not isinstance(roots, list) or not roots:
            return None

    # ---- Guard is ACTIVE for this session. Resolve inputs fail-CLOSED ----
    # Allowlist: CEO_SESSION_ROOTS_ALLOW, os.pathsep-separated directory
    # list, compared by realpath.
    allow_rps: Set[str] = set()
    for tok in (src_env.get(_SESSION_ROOTS_ALLOW_ENV) or "").split(os.pathsep):
        tok = tok.strip()
        if not tok:
            continue
        try:
            allow_rps.add(os.path.realpath(tok))
        except (OSError, ValueError):
            continue  # a broken allowlist token allows nothing

    # Resolve inputs + partition repo-internal vs external through the SHARED
    # core (also used by the corrupt-registry FXγ branch above) so the two
    # sites cannot drift on what "external" means. Uncanonicalizable input →
    # fail-CLOSED; repo-internal candidates are governed by the canonical
    # stack above and are dropped.
    uncanon_reason, external = _session_roots_partition_external(
        candidate_paths, repo_root
    )
    if uncanon_reason is not None:
        return uncanon_reason
    if not external:
        return None

    if sid_missing_with_registry:
        # M1 fail-CLOSED: session identity is absent but the registry is
        # non-empty and this event has external write targets → deny.
        return (
            "SESSION-ROOTS-WRITE-BLOCKED: session_id_missing — this "
            "canonical-edit event carries no session_id (absent/empty) "
            "while the session-roots registry holds registered workspace "
            "roots, so the write cannot be bound to a session and the "
            "boundary is unknowable. Writes outside the project root are "
            "denied fail-closed so that clearing CLAUDE_SESSION_ID cannot "
            "neutralize the guard (CLAUDE.md §4; PLAN-163 T3.1 / ADR-183)."
        )

    for entry in roots:
        directory = entry.get("directory") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or entry.get("unparseable")
            or not isinstance(directory, str)
            or not directory
            or "\x00" in directory
            or not os.path.isabs(directory)
        ):
            # A root WAS registered for this session but its boundary is
            # unknowable (observer marked it unparseable, the entry is
            # structurally malformed, or — M2 — its `directory` is not an
            # ABSOLUTE path: a relative value would be silently resolved
            # against the process CWD by os.path.realpath below and
            # mis-scope the boundary, so it is rejected in the same
            # fail-CLOSED class as unparseable). Like a corrupt whole-registry
            # (present-but-unparseable → fail-CLOSED for external writes), here
            # we positively know the session's write
            # surface grew and cannot bound it → every non-repo write is
            # denied until the entry is repaired (fail-CLOSED in the
            # consumer, PLAN-163 T3.1).
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_unparseable — this "
                "session has a registered workspace root whose directory could "
                "not be parsed (entry marked unparseable or malformed in "
                ".claude/state/session-roots.json), so the session's write "
                "boundary is unknowable. Writes outside the project root are "
                "denied fail-closed until the registry entry is repaired "
                "(PLAN-163 T3.1 / ADR-183)."
            )
        try:
            root_rp = os.path.realpath(directory)
        except Exception:
            return (
                "SESSION-ROOTS-WRITE-BLOCKED: session_root_unparseable — a "
                "registered workspace root for this session cannot be "
                "canonicalized (os.path.realpath raised); the session's write "
                "boundary is unknowable. Writes outside the project root are "
                "denied fail-closed (PLAN-163 T3.1 / ADR-183)."
            )
        if root_rp in allow_rps:
            continue  # Owner explicitly allowlisted this root
        for cand, rp in external:
            if rp == root_rp or rp.startswith(root_rp + os.sep):
                return (
                    "SESSION-ROOTS-WRITE-BLOCKED: session_root_write_denied — "
                    f"write target '{cand}' resolves to '{rp}', inside the "
                    f"session-registered workspace root '{root_rp}' "
                    f"(source={entry.get('source') or 'unknown'}). "
                    "DirectoryAdded (CC 2.1.220) is notification-only and "
                    "post-facto, so added roots are writable-by-default at "
                    "the permission layer; this framework denies such writes "
                    "by default. To allow, add the root's realpath to "
                    f"{_SESSION_ROOTS_ALLOW_ENV} (os.pathsep-separated) and "
                    "retry. PLAN-163 T3.1 / ADR-183."
                )
    return None



def _audit_registry_unreadable(registry_path: Path, exc_name: str) -> None:
    """Best-effort tamper-observability emit for a corrupt / unreadable /
    unknown-schema session-roots registry (H5).

    The guard fails CLOSED for external writes on this condition (FXγ / C3:
    a present-but-unparseable registry is a security-matcher INPUT-parse
    failure, not an ABSENT-file INFRA allow) while allowing repo-internal
    writes. This emit runs UNCONDITIONALLY — before the external/internal
    partition — so that even the repo-internal allow path records the
    corruption: an adversary corrupting or truncating the repo-internal,
    agent-writable ``.claude/state/session-roots.json`` is both BLOCKED (for
    the external write it opened) and OBSERVABLE in the HMAC-chained audit
    log. Reuses the already-registered ``veto_triggered`` action (NO new
    action invented — see ADR-183 §Residuals) with a distinct ``reason_code``.
    hasattr-guarded; never raises; no-value-echo — the breadcrumb carries the
    registry PATH and the exception CLASS name only, never registry bytes or
    tool-input content.
    """
    try:
        from _lib import audit_emit
        if not hasattr(audit_emit, "emit_veto_triggered"):
            return
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="session_roots_registry_unreadable",
            reason_preview=(
                "session-roots registry unreadable/corrupt/unknown-schema; "
                "fail-CLOSED for external writes (FXγ) + tamper recorded; "
                f"exc={exc_name}; registry={registry_path}"
            ),
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return



def _audit_session_root_block(target: str) -> None:
    """Best-effort veto_triggered emit for a session-roots deny.

    Mirrors ``_audit_block``: never raises; no-value-echo (the breadcrumb
    carries the target PATH only, never tool-input content).
    """
    try:
        from _lib import audit_emit
        audit_emit.emit_veto_triggered(
            hook="check_canonical_edit",
            reason_code="session_root_write_denied",
            reason_preview=(
                f"blocked write under session-registered root; target={target}"
            ),
            blocked_tool=_blocked_tool_field(),  # PLAN162_FIX_9
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return
